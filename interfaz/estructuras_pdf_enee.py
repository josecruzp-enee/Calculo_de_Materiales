# interfaz/estructuras_pdf_enee.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional, Tuple, Dict, List, Any
import re
import io
import math

import pandas as pd
import streamlit as st

from interfaz.estructuras_comunes import (
    COLUMNAS_BASE,
    normalizar_columnas,
    materializar_df_a_archivo,
    expand_wide_to_long,
)

# -----------------------------------------
# Helpers de clasificación
# -----------------------------------------
# Punto en línea "limpia": P-11, P # 11, P 11, Punto 11, P11
_RE_PUNTO_LINEA = re.compile(
    r"^\s*(?:P(?:UNTO)?\s*[-#]?\s*|P)\s*(\d+)\s*$",
    re.IGNORECASE
)

# Punto dentro de una línea reconstruida (para no confundir con otras cosas)
_RE_PUNTO_EN_TEXTO = re.compile(
    r"(?:^|[\s,;])(?:P(?:UNTO)?\s*[-#]?\s*|P)\s*(\d+)(?=$|[\s,;:])",
    re.IGNORECASE
)

_RE_XY_APOYO = re.compile(r"^\s*(X:|Y:|Apoyo:)\b", re.IGNORECASE)

# Detecta CÓDIGO + (P) aunque (P) venga separado por espacios
# Nota: si en SHX viene "A-I-4" "(P)" como dos words, la línea reconstruida lo deja "A-I-4 (P)"
_RE_CODIGO_CON_P = re.compile(
    r"""
    (?P<code>
        (?:PC|PM|PT)-[A-Z0-9"'\-]+
        |A-[A-Z0-9\-]+
        |B-[A-Z0-9\-]+
        |CT-[A-Z0-9\-]+
        |TS-[A-Z0-9\-]+
        |TD[A-Z0-9\-]*|TF[A-Z0-9\-]*|TR[A-Z0-9\-]*|TX[A-Z0-9\-]*
        |LL-[A-Z0-9\-]+|LS-[A-Z0-9\-]+
        |R-\d+[A-Z0-9\-]*
    )
    \s*\(\s*[Pp]\s*\)
    """,
    re.VERBOSE
)

# Multiplicador explícito al inicio
_RE_MULT = re.compile(r"^\s*(\d+)\s*[x×]\s*(.+?)\s*$", flags=re.I)


def _punto_label(num: str) -> str:
    return f"Punto {int(num)}"


def _limpiar_item(item: str) -> str:
    s = (item or "").strip().strip('"').strip("'")
    s = re.sub(r"\s+", " ", s)
    return s


def _clasificar_item(code: str) -> Optional[str]:
    c = code.strip().upper()

    if c.startswith(("PC-", "PM-", "PT-")):
        return "Poste"
    if c.startswith("A-"):
        return "Primario"
    if c.startswith("B-"):
        return "Secundario"
    if re.match(r"^\d*\s*R[-\s]*\d+", c) or c.startswith("R-"):
        return "Retenidas"
    if c.startswith("CT-"):
        return "Conexiones a tierra"
    if c.startswith(("TS-", "TD", "TF", "TR", "TX")):
        return "Transformadores"
    if c.startswith(("LL-", "LS-")):
        return "Luminarias"

    return None


def _agregar_en_bucket(bucket: Dict[str, Dict[str, int]], col: str, raw_item: str) -> None:
    """
    Regla:
    - Por defecto, cada código cuenta 1 vez por Punto (dedupe).
    - Si el texto trae 2x/3x/2×, se respeta ese multiplicador.
    """
    item = _limpiar_item(raw_item)
    if not item:
        return

    m = _RE_MULT.match(item)
    if m:
        qty = int(m.group(1))
        code = _limpiar_item(m.group(2))
        if not code:
            return
        bucket[col][code] = max(bucket[col].get(code, 0), qty)
        return

    bucket[col][item] = max(bucket[col].get(item, 0), 1)


def _bucket_to_row(punto: str, bucket: Dict[str, Dict[str, int]]) -> Dict[str, str]:
    row = {c: "" for c in COLUMNAS_BASE}
    row["Punto"] = punto

    for col in COLUMNAS_BASE:
        if col == "Punto":
            continue

        codes = bucket.get(col, {})
        if not codes:
            row[col] = ""
            continue

        parts: List[str] = []
        for code in sorted(codes.keys()):
            qty = int(codes.get(code, 1))
            parts.append(f"{qty}x {code}" if qty > 1 else code)

        row[col] = " ".join(parts)

    return row


def extraer_codigos_proyectados(texto_linea: str) -> List[str]:
    if not texto_linea:
        return []
    t = " ".join((texto_linea or "").split())
    out: List[str] = []
    for m in _RE_CODIGO_CON_P.finditer(t):
        cod = (m.group("code") or "").strip()
        if cod:
            out.append(cod)
    return out


# ============================================================
# 1) Reconstrucción robusta de "líneas" usando extract_words()
# ============================================================
def _words_de_pdf(pdf) -> List[Dict[str, Any]]:
    """
    Devuelve words con coordenadas (pdfplumber).
    """
    words_all: List[Dict[str, Any]] = []
    for pi, page in enumerate(pdf.pages):
        try:
            words = page.extract_words(
                use_text_flow=True,
                keep_blank_chars=False,
                extra_attrs=["fontname", "size"],
            ) or []
        except Exception:
            words = page.extract_words() or []

        for w in words:
            # normaliza campos útiles
            w2 = dict(w)
            w2["page_index"] = pi
            # centro
            w2["cx"] = (float(w2.get("x0", 0.0)) + float(w2.get("x1", 0.0))) / 2.0
            w2["cy"] = (float(w2.get("top", 0.0)) + float(w2.get("bottom", 0.0))) / 2.0
            w2["text"] = (w2.get("text") or "").strip()
            if w2["text"]:
                words_all.append(w2)

    # orden por página, y, x
    words_all.sort(key=lambda a: (a["page_index"], float(a.get("top", 0.0)), float(a.get("x0", 0.0))))
    return words_all


def _reconstruir_lineas(words: List[Dict[str, Any]], y_tol: float = 2.5, x_gap: float = 6.0) -> List[Dict[str, Any]]:
    """
    Agrupa words en líneas por cercanía vertical (y_tol) y une texto si el gap horizontal es pequeño.
    Retorna lista de dicts: {page_index, text, x0, x1, top, bottom, cx, cy}
    """
    lines: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = []
    current_y: Optional[float] = None
    current_page: Optional[int] = None

    for w in words:
        y = float(w.get("top", 0.0))
        pi = int(w.get("page_index", 0))

        if not current:
            current = [w]
            current_y = y
            current_page = pi
            continue

        # nueva línea si cambia mucho y o cambia página
        if pi != current_page or current_y is None or abs(y - current_y) > y_tol:
            lines.append(current)
            current = [w]
            current_y = y
            current_page = pi
        else:
            current.append(w)

    if current:
        lines.append(current)

    out: List[Dict[str, Any]] = []
    for group in lines:
        group.sort(key=lambda a: float(a.get("x0", 0.0)))
        parts: List[str] = []
        x1_prev: Optional[float] = None

        x0 = min(float(a.get("x0", 0.0)) for a in group)
        x1 = max(float(a.get("x1", 0.0)) for a in group)
        top = min(float(a.get("top", 0.0)) for a in group)
        bottom = max(float(a.get("bottom", 0.0)) for a in group)
        pi = int(group[0].get("page_index", 0))

        for a in group:
            txt = (a.get("text") or "").strip()
            if not txt:
                continue
            x0a = float(a.get("x0", 0.0))
            if x1_prev is None:
                parts.append(txt)
            else:
                gap = x0a - x1_prev
                # si están muy cerca, sepárala con espacio (no pegado) para que "(P)" quede "(P)"
                parts.append(txt if gap <= 0.5 else (" " + txt))
            x1_prev = float(a.get("x1", 0.0))

        text_line = "".join(parts).strip()
        if not text_line:
            continue

        out.append({
            "page_index": pi,
            "text": text_line,
            "x0": x0, "x1": x1, "top": top, "bottom": bottom,
            "cx": (x0 + x1) / 2.0,
            "cy": (top + bottom) / 2.0,
        })

    return out


# ============================================================
# 2) Parser por texto reconstruido (mejor que extract_text())
# ============================================================
def extraer_estructuras_desde_lineas(lineas: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Intenta construir puntos por "bloques" (punto + líneas siguientes hasta X/Y).
    Funciona bien cuando el PDF conserva el bloque de texto del MTEXT.
    """
    if not lineas:
        return pd.DataFrame(columns=COLUMNAS_BASE)

    bloques: Dict[str, Dict[str, Dict[str, int]]] = {}
    punto_actual: Optional[str] = None
    punto_cerrado: bool = False

    for ln in lineas:
        t = (ln.get("text") or "").strip()
        if not t:
            continue

        # Punto línea
        m = _RE_PUNTO_LINEA.match(t)
        if m:
            punto_actual = _punto_label(m.group(1))
            bloques.setdefault(punto_actual, {c: {} for c in COLUMNAS_BASE if c != "Punto"})
            punto_cerrado = False
            continue

        # Punto dentro del texto
        m2 = _RE_PUNTO_EN_TEXTO.search(t)
        if m2:
            punto_actual = _punto_label(m2.group(1))
            bloques.setdefault(punto_actual, {c: {} for c in COLUMNAS_BASE if c != "Punto"})
            punto_cerrado = False
            # no continue: por si trae códigos en la misma línea

        if punto_actual is None:
            continue

        if punto_cerrado:
            continue

        if _RE_XY_APOYO.match(t) or "APOYO:" in t.upper():
            punto_cerrado = True
            continue

        codigos_p = extraer_codigos_proyectados(t)
        if not codigos_p:
            continue

        for code in codigos_p:
            code = _limpiar_item(code)
            col = _clasificar_item(code)
            if col:
                _agregar_en_bucket(bloques[punto_actual], col, code)

    rows = [_bucket_to_row(p, b) for p, b in bloques.items()]
    df = pd.DataFrame(rows, columns=COLUMNAS_BASE)

    if not df.empty:
        cols_no_punto = [c for c in COLUMNAS_BASE if c != "Punto"]
        df = df[df[cols_no_punto].astype(str).apply(lambda r: any(v.strip() for v in r), axis=1)]

    return normalizar_columnas(df, COLUMNAS_BASE)


# ============================================================
# 3) Fallback: clustering espacial de códigos (P)
# ============================================================
def _dist(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    dx = float(a["cx"]) - float(b["cx"])
    dy = float(a["cy"]) - float(b["cy"])
    return math.hypot(dx, dy)


def _clusterizar_puntos(items: List[Dict[str, Any]], eps: float = 35.0) -> List[List[Dict[str, Any]]]:
    """
    Clustering simple (sin sklearn): une elementos si están a distancia <= eps.
    """
    clusters: List[List[Dict[str, Any]]] = []
    used = [False] * len(items)

    for i in range(len(items)):
        if used[i]:
            continue
        used[i] = True
        cluster = [items[i]]

        # expansión tipo BFS
        q = [i]
        while q:
            j = q.pop()
            for k in range(len(items)):
                if used[k]:
                    continue
                if items[k]["page_index"] != items[j]["page_index"]:
                    continue
                if _dist(items[k], items[j]) <= eps:
                    used[k] = True
                    cluster.append(items[k])
                    q.append(k)

        clusters.append(cluster)

    # ordena clusters de arriba-abajo / izquierda-derecha por centro
    clusters.sort(key=lambda cl: (min(x["page_index"] for x in cl), sum(x["cy"] for x in cl)/len(cl), sum(x["cx"] for x in cl)/len(cl)))
    return clusters


def extraer_estructuras_por_cercania(lineas: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Extrae todos los códigos (P) con coordenadas, clusteriza por cercanía y crea "puntos".
    Si se puede, asigna el número de punto buscando un texto "P-xx" cercano al cluster.
    """
    # 1) recolecta ocurrencias de códigos (P)
    ocurrencias: List[Dict[str, Any]] = []
    puntos_texto: List[Dict[str, Any]] = []

    for ln in lineas:
        t = (ln.get("text") or "").strip()
        if not t:
            continue

        # detectores de "P-xx" cercanos (anclas)
        m = _RE_PUNTO_EN_TEXTO.search(t)
        if m:
            puntos_texto.append({
                "page_index": ln["page_index"],
                "num": int(m.group(1)),
                "cx": ln["cx"], "cy": ln["cy"],
            })

        # códigos (P)
        cods = extraer_codigos_proyectados(t)
        for c in cods:
            ocurrencias.append({
                "page_index": ln["page_index"],
                "code": _limpiar_item(c),
                "cx": ln["cx"], "cy": ln["cy"],
            })

    if not ocurrencias:
        return pd.DataFrame(columns=COLUMNAS_BASE)

    # 2) clusteriza ocurrencias -> clusters = puntos
    clusters = _clusterizar_puntos(ocurrencias, eps=35.0)

    # 3) arma bloques
    bloques: Dict[str, Dict[str, Dict[str, int]]] = {}
    punto_auto = 1

    for cl in clusters:
        # intenta asignar número de punto por ancla más cercana
        cx = sum(x["cx"] for x in cl) / len(cl)
        cy = sum(x["cy"] for x in cl) / len(cl)
        pi = cl[0]["page_index"]

        candidato: Optional[int] = None
        mejor = 1e18
        for p in puntos_texto:
            if p["page_index"] != pi:
                continue
            d = math.hypot(float(p["cx"]) - cx, float(p["cy"]) - cy)
            if d < mejor and d <= 120.0:  # radio razonable
                mejor = d
                candidato = int(p["num"])

        if candidato is not None:
            punto = f"Punto {candidato}"
        else:
            punto = f"Punto {punto_auto}"
            punto_auto += 1

        bloques.setdefault(punto, {c: {} for c in COLUMNAS_BASE if c != "Punto"})

        for it in cl:
            code = it["code"]
            col = _clasificar_item(code)
            if col:
                _agregar_en_bucket(bloques[punto], col, code)

    rows = [_bucket_to_row(p, b) for p, b in bloques.items()]
    df = pd.DataFrame(rows, columns=COLUMNAS_BASE)

    if not df.empty:
        cols_no_punto = [c for c in COLUMNAS_BASE if c != "Punto"]
        df = df[df[cols_no_punto].astype(str).apply(lambda r: any(v.strip() for v in r), axis=1)]

    # orden numérico si es posible
    def _k(p: str) -> int:
        m = re.search(r"(\d+)", p)
        return int(m.group(1)) if m else 10**9

    df = df.sort_values(by="Punto", key=lambda s: s.map(_k)).reset_index(drop=True)
    return normalizar_columnas(df, COLUMNAS_BASE)


def extraer_estructuras_desde_pdf(pdf) -> pd.DataFrame:
    """
    Estrategia:
    1) Reconstruir líneas (extract_words)
    2) Intentar parser por bloques (punto + hasta X/Y)
    3) Si salen muy pocos puntos, usar clustering por cercanía (fallback)
    """
    words = _words_de_pdf(pdf)
    lineas = _reconstruir_lineas(words, y_tol=2.5, x_gap=6.0)

    df1 = extraer_estructuras_desde_lineas(lineas)

    # Heurística: si detecta MUY pocos puntos, el PDF es SHX/fragmentado -> fallback
    if df1.empty or len(df1) < 6:
        df2 = extraer_estructuras_por_cercania(lineas)
        return df2

    return df1


# -----------------------------------------
# UI Streamlit: modo PDF
# -----------------------------------------
def cargar_desde_pdf_enee() -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    st.subheader("📄 Cargar estructuras desde PDF (ENEE)")

    archivo_pdf = st.file_uploader("Sube el PDF del plano", type=["pdf"], key="upl_pdf")
    if not archivo_pdf:
        return None, None

    try:
        import pdfplumber  # type: ignore
    except Exception:
        st.error("Falta dependencia: pdfplumber. Agrega 'pdfplumber' a requirements.txt")
        return None, None

    with pdfplumber.open(io.BytesIO(archivo_pdf.getvalue())) as pdf:
        df_ancho = extraer_estructuras_desde_pdf(pdf)

    if df_ancho.empty:
        st.warning("Se leyó el PDF, pero no se encontraron estructuras PROYECTADAS (P).")
        return None, None

    st.success(f"✅ Estructuras proyectadas detectadas: {len(df_ancho)} puntos")
    st.dataframe(df_ancho, use_container_width=True, hide_index=True)

    ruta_tmp = materializar_df_a_archivo(df_ancho, "pdf")
    df_largo = expand_wide_to_long(df_ancho)

    st.caption("🔎 Vista LARGA (lo que consume el motor)")
    st.dataframe(df_largo, use_container_width=True, hide_index=True)

    return df_largo, ruta_tmp
