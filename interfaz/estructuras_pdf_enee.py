# interfaz/estructuras_pdf_enee.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional, Tuple, Dict, List
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

# -----------------------------------------
# Helpers de clasificación
# -----------------------------------------
_RE_PUNTO = re.compile(r"^\s*P\s*[-#]?\s*(\d+)\s*$", re.IGNORECASE)
_RE_PUNTO_EN_LINEA = re.compile(
    r"(?:^|[\s,;])P\s*[-#]?\s*(\d+)(?=$|[\s,;:])",
    re.IGNORECASE
)
_RE_XY_APOYO = re.compile(r"^\s*(X:|Y:|Apoyo:)\b", re.IGNORECASE)

# ✅ Detecta (qty opcional) + CODIGO seguido por (P) en cualquier parte del texto.
# Ejemplos:
#   "CT-N (P) ..."          -> "CT-N"
#   "2x LS-1 (P) ..."       -> "2x LS-1"
#   "3× PT-30 (P)"          -> "3x PT-30"
_RE_CODIGO_CON_P = re.compile(
    r"""
    (?:
        (?P<qty>\d+)\s*[x×]\s*     # 2x / 2× opcional
    )?
    (?P<code>
        (?:PC|PM|PT)-[A-Z0-9"'\-]+
        |A-[A-Z0-9\-]+
        |B-[A-Z0-9\-]+
        |CT-[A-Z0-9\-]+
        |TS-[A-Z0-9\-]+
        |TD[A-Z0-9\-]*|TF[A-Z0-9\-]*|TR[A-Z0-9\-]*|TX[A-Z0-9\-]*
        |LL-[A-Z0-9\-]+|LS-[A-Z0-9\-]+
        |R-\d+[A-Z0-9\-]*          # R-05T, R-2, etc.
    )
    \s*\(\s*[Pp]\s*\)
    """,
    re.VERBOSE
)


def _punto_label(num: str) -> str:
    n = int(num)
    return f"Punto {n}"


def _limpiar_item(item: str) -> str:
    s = (item or "").strip().strip('"').strip("'")
    s = re.sub(r"\s+", " ", s)
    return s


def _strip_qty_prefix(s: str) -> str:
    """Quita prefijo '2x ' / '3× ' si existiera, para clasificar por código."""
    s = (s or "").strip()
    s = re.sub(r"^\s*\d+\s*[x×]\s*", "", s, flags=re.I)
    return s.strip()


# ✅ Compatible con Python 3.8/3.9
def _clasificar_item(code: str) -> Optional[str]:
    c = _strip_qty_prefix(code).strip().upper()

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

    # detectar multiplicador explícito al inicio: 2x CODE, 3× CODE
    m = re.match(r"^\s*(\d+)\s*[x×]\s*(.+?)\s*$", item, flags=re.I)
    if m:
        qty = int(m.group(1))
        code = _limpiar_item(m.group(2))
        if not code:
            return
        # si aparece varias veces, nos quedamos con el máximo (por seguridad)
        bucket[col][code] = max(bucket[col].get(code, 0), qty)
        return

    # sin multiplicador: SOLO 1 por Punto
    bucket[col][item] = 1


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

        # orden alfabético para consistencia
        parts = []
        for code in sorted(codes.keys()):
            qty = int(codes.get(code, 1))
            if qty > 1:
                parts.append(f"{qty}x {code}")
            else:
                parts.append(code)

        row[col] = " ".join(parts)

    return row


def extraer_codigos_proyectados(linea: str) -> List[str]:
    """
    Devuelve items proyectados del tipo:
      - 'CODE' si no hay multiplicador
      - '2x CODE' si hay multiplicador explícito
    """
    if not linea:
        return []
    t = " ".join((linea or "").split())
    out: List[str] = []

    for m in _RE_CODIGO_CON_P.finditer(t):
        cod = (m.group("code") or "").strip()
        qty = (m.group("qty") or "").strip()
        if not cod:
            continue
        if qty:
            out.append(f"{qty}x {cod}")
        else:
            out.append(cod)

    return out


# -----------------------------------------
# Parser principal (texto extraído del PDF)
# -----------------------------------------
def extraer_estructuras_desde_texto_pdf(texto: str) -> pd.DataFrame:
    if not texto or not texto.strip():
        return pd.DataFrame(columns=COLUMNAS_BASE)

    lines = [ln.rstrip() for ln in texto.splitlines()]

    # ✅ coherente con bucket dict[str,int]
    bloques: Dict[str, Dict[str, Dict[str, int]]] = {}

    punto_actual: Optional[str] = None
    punto_cerrado: bool = False  # ✅ evita “arrastre” después de X/Y/Apoyo

    for ln in lines:
        t = (ln or "").strip()
        if not t:
            continue

        # 1) Punto en línea limpia (ej: "P-11" o "P # 11")
        m = _RE_PUNTO.match(t)
        if m:
            punto_actual = _punto_label(m.group(1))
            bloques.setdefault(punto_actual, {c: {} for c in COLUMNAS_BASE if c != "Punto"})
            punto_cerrado = False  # ✅ reabrir bloque
            continue

        # 2) Punto dentro de línea (ej: "P-08 Apoyo: 4014499")
        m2 = _RE_PUNTO_EN_LINEA.search(t)
        if m2:
            punto_actual = _punto_label(m2.group(1))
            bloques.setdefault(punto_actual, {c: {} for c in COLUMNAS_BASE if c != "Punto"})
            punto_cerrado = False  # ✅ reabrir bloque
            # no hacemos continue; por si en esa misma línea viene texto útil

        if punto_actual is None:
            continue

        # ✅ Si ya llegamos a X/Y/Apoyo, NO aceptamos más estructuras para este punto
        if punto_cerrado:
            continue

        # ✅ cerrar lectura del punto cuando aparezca X/Y/Apoyo
        if _RE_XY_APOYO.match(t) or "APOYO:" in t.upper():
            punto_cerrado = True
            continue

        # ✅ SOLO códigos con (P) (y con qty si venía 2x/3x)
        codigos_p = extraer_codigos_proyectados(t)
        if not codigos_p:
            continue

        for item in codigos_p:
            item = _limpiar_item(item)
            if not item:
                continue

            col = _clasificar_item(item)
            if col:
                _agregar_en_bucket(bloques[punto_actual], col, item)

    rows = [_bucket_to_row(p, b) for p, b in bloques.items()]
    df = pd.DataFrame(rows, columns=COLUMNAS_BASE)

    if not df.empty:
        cols_no_punto = [c for c in COLUMNAS_BASE if c != "Punto"]
        df = df[df[cols_no_punto].astype(str).apply(lambda r: any(v.strip() for v in r), axis=1)]

    return normalizar_columnas(df, COLUMNAS_BASE)


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

    texto_total: List[str] = []
    with pdfplumber.open(io.BytesIO(archivo_pdf.getvalue())) as pdf:
        for page in pdf.pages:
            texto_total.append(page.extract_text() or "")

    texto_total_str = "\n".join(texto_total).strip()
    if not texto_total_str:
        st.warning("No se detectó texto en el PDF. Si el plano es escaneado (imagen), tocaría OCR.")
        return None, None

    df_ancho = extraer_estructuras_desde_texto_pdf(texto_total_str)
    if df_ancho.empty:
        st.warning("Se leyó el PDF, pero no se encontraron estructuras PROYECTADAS (P).")
        return None, None

    st.success(f"✅ Estructuras proyectadas detectadas: {len(df_ancho)} puntos")
    st.dataframe(df_ancho, use_container_width=True, hide_index=True)

    ruta_tmp = materializar_df_a_archivo(df_ancho, "pdf")
    df_largo = expand_wide_to_long(df_ancho)

    # ✅ consolidar por seguridad (evita duplicado por cualquier ruta rara)
    if not df_largo.empty:
        df_largo = (
            df_largo.groupby(["Punto", "codigodeestructura"], as_index=False)["cantidad"]
            .sum()
        )

    st.caption("🔎 Vista LARGA (lo que consume el motor)")
    st.dataframe(df_largo, use_container_width=True, hide_index=True)

    return df_largo, ruta_tmp
