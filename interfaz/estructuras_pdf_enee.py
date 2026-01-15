# interfaz/estructuras_pdf_enee.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional, Tuple, Dict, List, Any
import re
import io

import pandas as pd
import streamlit as st

from interfaz.estructuras_comunes import (
    COLUMNAS_BASE,
    normalizar_columnas,
    materializar_df_a_archivo,
    expand_wide_to_long,
)

# =============================================================================
# Regex y helpers
# =============================================================================

# Línea tipo: "P-11", "P # 11", "P 11", "PUNTO 11"
_RE_LINEA_PUNTO = re.compile(r"^\s*(?:P|PUNTO)\s*[-#]?\s*(\d+)\s*$", re.IGNORECASE)

# Para detectar códigos con (P) dentro del texto (ya reconstruido por líneas)
_RE_CODIGO_CON_P = re.compile(
    r"""
    (?P<prefix_qty>\b\d+\s*[x×]\s*)?      # opcional: "2x " o "3× "
    (?P<code>
        (?:PC|PM|PT)-[A-Z0-9"'\-]+
        |A-[A-Z0-9\-]+
        |B-[A-Z0-9\-]+
        |CT-[A-Z0-9\-]+
        |TS-[A-Z0-9\-]+
        |TD[A-Z0-9\-]*|TF[A-Z0-9\-]*|TR[A-Z0-9\-]*|TX[A-Z0-9\-]*
        |LL-[A-Z0-9\-]+|LS-[A-Z0-9\-]+
        |R-\d+[A-Z0-9\-]*                 # R-05T, R-2, etc.
        |CS-\d+[A-Z0-9\-]*                # CS-2 (P), por si aplica
    )
    \s*\(\s*[Pp]\s*\)
    """,
    re.VERBOSE,
)

_RE_XY_APOYO_LINE = re.compile(r"^\s*(X:|Y:|APOYO:)\b", re.IGNORECASE)


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
    if c.startswith("R-"):
        return "Retenidas"
    if c.startswith("CT-"):
        return "Conexiones a tierra"
    if c.startswith(("TS-", "TD", "TF", "TR", "TX")):
        return "Transformadores"
    if c.startswith(("LL-", "LS-")):
        return "Luminarias"

    # Si quieres soportar CS-2 (P) como “Otros”, tendrías que agregar columna.
    # Por ahora lo ignoramos (o lo puedes mapear a "Conexiones a tierra" si te conviene).
    return None


def _agregar_en_bucket(bucket: Dict[str, Dict[str, int]], col: str, code: str, qty: int) -> None:
    """
    Regla:
      - Si no hay multiplicador explícito, qty=1 y se dedupe por punto.
      - Si hay 2x/3x, se respeta el máximo (no se suma para evitar inflado por duplicación del PDF).
    """
    code = _limpiar_item(code)
    if not code:
        return
    prev = int(bucket[col].get(code, 0))
    bucket[col][code] = max(prev, int(qty))


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

        parts = []
        for code in sorted(codes.keys()):
            qty = int(codes.get(code, 1))
            parts.append(f"{qty}x {code}" if qty > 1 else code)

        # en ANCHO lo juntamos con espacio (más compacto y no “infla” con saltos)
        row[col] = " ".join(parts)

    return row


# =============================================================================
# Utilidades PDF -> words -> líneas -> bloques
# =============================================================================

def _cluster_lines(words: List[Dict[str, Any]], y_tol: float = 2.5) -> List[List[Dict[str, Any]]]:
    """
    Agrupa palabras en líneas usando 'top' con tolerancia.
    Devuelve lista de líneas, cada línea es lista de words ordenados por x0.
    """
    if not words:
        return []

    # ordenar por y, luego x
    ws = sorted(words, key=lambda w: (float(w.get("top", 0.0)), float(w.get("x0", 0.0))))

    lines: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = []
    current_y: Optional[float] = None

    for w in ws:
        y = float(w.get("top", 0.0))
        if current_y is None:
            current_y = y
            current = [w]
            continue

        if abs(y - current_y) <= y_tol:
            current.append(w)
        else:
            current = sorted(current, key=lambda ww: float(ww.get("x0", 0.0)))
            lines.append(current)
            current_y = y
            current = [w]

    if current:
        current = sorted(current, key=lambda ww: float(ww.get("x0", 0.0)))
        lines.append(current)

    return lines


def _line_text(line_words: List[Dict[str, Any]]) -> str:
    return " ".join([str(w.get("text", "")).strip() for w in line_words if str(w.get("text", "")).strip()])


def _detect_point_anchors(lines: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Detecta líneas que sean punto (P-XX / P # XX / P XX / PUNTO XX).
    Retorna anclas con: num, top, x0.
    """
    anchors: List[Dict[str, Any]] = []
    for lw in lines:
        txt = _line_text(lw)
        # normalizamos casos comunes: "P" "#" "11" -> "P # 11"
        txt_norm = re.sub(r"\s+", " ", txt).strip()

        m = _RE_LINEA_PUNTO.match(txt_norm)
        if not m:
            # a veces viene separado raro, intentamos compactar: "P- 11"
            txt_norm2 = txt_norm.replace("P -", "P-").replace("P #", "P # ")
            m = _RE_LINEA_PUNTO.match(txt_norm2)

        if m:
            num = m.group(1)
            anchors.append({
                "num": int(num),
                "top": float(lw[0].get("top", 0.0)),
                "x0": float(min(w.get("x0", 0.0) for w in lw)),
                "x1": float(max(w.get("x1", 0.0) for w in lw)),
            })

    # ordenar por y (de arriba a abajo)
    anchors.sort(key=lambda a: a["top"])
    return anchors


def _extract_block_lines_for_anchor(
    all_words: List[Dict[str, Any]],
    anchor: Dict[str, Any],
    next_anchor_top: Optional[float],
    x_pad_left: float = 8.0,
    x_width: float = 190.0,
    y_pad_top: float = 2.0,
    y_pad_bottom: float = 2.0,
) -> List[str]:
    """
    Devuelve líneas (texto) dentro del “bloque” del punto:
      - x cerca de la columna del P
      - y debajo del P hasta antes del siguiente P
    """
    ax0 = float(anchor["x0"])
    atop = float(anchor["top"])

    y_min = atop + y_pad_top
    y_max = (float(next_anchor_top) - y_pad_bottom) if next_anchor_top is not None else (atop + 250.0)

    x_min = ax0 - x_pad_left
    x_max = ax0 + x_width

    region = [
        w for w in all_words
        if (float(w.get("top", 0.0)) >= y_min and float(w.get("top", 0.0)) <= y_max)
        and (float(w.get("x0", 0.0)) >= x_min and float(w.get("x0", 0.0)) <= x_max)
    ]

    # agrupar a líneas
    lines = _cluster_lines(region, y_tol=2.5)
    out_txt = []
    for lw in lines:
        t = _line_text(lw).strip()
        if not t:
            continue
        # cortamos si aparece X/Y/Apoyo
        if _RE_XY_APOYO_LINE.match(t):
            break
        out_txt.append(t)
    return out_txt


def _parse_codes_from_block_lines(block_lines: List[str]) -> Dict[str, Dict[str, int]]:
    """
    Convierte líneas del bloque a bucket por categoría:
      {"Poste": {"PT-30":1}, "Secundario":{"B-II-4":1}, ...}
    Solo toma códigos marcados (P). Respeta 2x/3x.
    """
    bucket: Dict[str, Dict[str, int]] = {c: {} for c in COLUMNAS_BASE if c != "Punto"}

    for line in block_lines:
        # buscamos todos los (P) en la línea
        for m in _RE_CODIGO_CON_P.finditer(line):
            code = _limpiar_item(m.group("code") or "")
            if not code:
                continue

            qty = 1
            pref = (m.group("prefix_qty") or "").strip()
            if pref:
                mm = re.match(r"(\d+)\s*[x×]\s*", pref, flags=re.I)
                if mm:
                    qty = int(mm.group(1))

            col = _clasificar_item(code)
            if col:
                _agregar_en_bucket(bucket, col, code, qty)

    return bucket


def extraer_estructuras_desde_pdf_por_bloques(pdf_bytes: bytes) -> pd.DataFrame:
    """
    Lee el PDF por words (coordenadas), detecta Puntos y arma bloques verticales.
    Devuelve DF ANCHO con COLUMNAS_BASE.
    """
    try:
        import pdfplumber  # type: ignore
    except Exception:
        st.error("Falta dependencia: pdfplumber. Agrega 'pdfplumber' a requirements.txt")
        return pd.DataFrame(columns=COLUMNAS_BASE)

    acumulado: Dict[int, Dict[str, Dict[str, int]]] = {}  # punto_num -> bucket

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            # words = texto con coordenadas
            words = page.extract_words(
                use_text_flow=True,
                keep_blank_chars=False,
            ) or []

            if not words:
                continue

            # líneas de toda la página (solo para detectar anclas)
            page_lines = _cluster_lines(words, y_tol=2.5)
            anchors = _detect_point_anchors(page_lines)
            if not anchors:
                continue

            for i, a in enumerate(anchors):
                next_top = anchors[i + 1]["top"] if i + 1 < len(anchors) else None
                block_lines = _extract_block_lines_for_anchor(words, a, next_top)

                # bucket del bloque
                bucket_block = _parse_codes_from_block_lines(block_lines)

                # fusionamos al acumulado por punto sin duplicar
                pnum = int(a["num"])
                if pnum not in acumulado:
                    acumulado[pnum] = bucket_block
                else:
                    # merge por máximo (evita inflado si el PDF repite el bloque)
                    for col, codes in bucket_block.items():
                        for code, qty in codes.items():
                            prev = int(acumulado[pnum][col].get(code, 0))
                            acumulado[pnum][col][code] = max(prev, int(qty))

    # construir DF
    rows = []
    for pnum in sorted(acumulado.keys()):
        punto = _punto_label(str(pnum))
        row = _bucket_to_row(punto, acumulado[pnum])
        rows.append(row)

    df = pd.DataFrame(rows, columns=COLUMNAS_BASE)

    # eliminar filas vacías
    if not df.empty:
        cols_no_punto = [c for c in COLUMNAS_BASE if c != "Punto"]
        df = df[df[cols_no_punto].astype(str).apply(lambda r: any(v.strip() for v in r), axis=1)]

    return normalizar_columnas(df, COLUMNAS_BASE)


# =============================================================================
# UI Streamlit
# =============================================================================

def cargar_desde_pdf_enee() -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    st.subheader("📄 Cargar estructuras desde PDF (ENEE)")

    archivo_pdf = st.file_uploader("Sube el PDF del plano", type=["pdf"], key="upl_pdf")
    if not archivo_pdf:
        return None, None

    pdf_bytes = archivo_pdf.getvalue()
    if not pdf_bytes:
        return None, None

    df_ancho = extraer_estructuras_desde_pdf_por_bloques(pdf_bytes)
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
