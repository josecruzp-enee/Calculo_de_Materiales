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
    split_cell_items,
    es_proyectada,   # <- la que ya creaste
)

# -----------------------------------------
# Helpers de clasificación
# -----------------------------------------
_RE_PUNTO = re.compile(r"^\s*P\s*#\s*(\d+)\s*$", re.IGNORECASE)
_RE_XY_APOYO = re.compile(r"^\s*(X:|Y:|Apoyo:)\b", re.IGNORECASE)

def _punto_label(num: str) -> str:
    n = int(num)
    return f"Punto {n}"

def _limpiar_item(item: str) -> str:
    # quita comillas, espacios, etc.
    s = (item or "").strip().strip('"').strip("'")
    s = re.sub(r"\s+", " ", s)
    return s

def _clasificar_item(code: str) -> str | None:
    """
    Devuelve a qué columna ANCHA va.
    """
    c = code.strip().upper()

    # Poste
    if c.startswith(("PC-", "PM-", "PT-")):
        return "Poste"

    # Primario
    if c.startswith("A-"):
        return "Primario"

    # Secundario
    if c.startswith("B-"):
        return "Secundario"

    # Retenidas (permite 2R-2, R-02, etc)
    if re.match(r"^\d*\s*R[-\s]*\d+", c) or c.startswith("R-"):
        return "Retenidas"

    # Tierra
    if c.startswith("CT-"):
        return "Conexiones a tierra"

    # Transformadores típicos
    if c.startswith(("TS-", "TD", "TF", "TR", "TX")):
        return "Transformadores"

    # Luminarias
    if c.startswith(("LL-", "LS-")):
        return "Luminarias"

    return None

def _agregar_en_bucket(bucket: Dict[str, List[str]], col: str, raw_item: str):
    """
    Guarda en el bucket ya como string, manteniendo cantidad si venía pegada tipo 2R-2(P).
    """
    item = _limpiar_item(raw_item)

    # Si viene pegado "2R-2 (P)" o "2R-2(P)" lo dejamos igual (tu expand_wide_to_long ya entiende 2x / 2 CODE / 2CODE)
    # Pero si viene "2R-2" sin x, tu parse_item lo interpreta como qty pegada (2CODE) solo si empieza con número + letra.
    # En R-2 empieza con número + 'R' (letra), así que funciona bien.
    bucket[col].append(item)

def _bucket_to_row(punto: str, bucket: Dict[str, List[str]]) -> Dict[str, str]:
    row = {c: "" for c in COLUMNAS_BASE}
    row["Punto"] = punto
    for col in COLUMNAS_BASE:
        if col == "Punto":
            continue
        vals = bucket.get(col, [])
        # Junta por salto de línea (mejor que coma, porque luego tu split_cell_items separa)
        row[col] = "\n".join([_limpiar_item(v) for v in vals if _limpiar_item(v)])
    return row


# -----------------------------------------
# Parser principal (texto extraído del PDF)
# -----------------------------------------
def extraer_estructuras_desde_texto_pdf(texto: str) -> pd.DataFrame:
    """
    Devuelve DF ANCHO con solo (P).
    """
    if not texto or not texto.strip():
        return pd.DataFrame(columns=COLUMNAS_BASE)

    lines = [ln.rstrip() for ln in texto.splitlines()]

    bloques: Dict[str, Dict[str, List[str]]] = {}
    punto_actual: str | None = None

    for ln in lines:
        t = (ln or "").strip()
        if not t:
            continue

        m = _RE_PUNTO.match(t)
        if m:
            punto_actual = _punto_label(m.group(1))
            if punto_actual not in bloques:
                bloques[punto_actual] = {c: [] for c in COLUMNAS_BASE if c != "Punto"}
            continue

        if punto_actual is None:
            continue

        # corta lectura si llegamos a X/Y/Apoyo (ya no son estructuras)
        if _RE_XY_APOYO.match(t):
            continue

        # En algunos PDFs viene "P # 08 Apoyo: 4014499" en la misma línea
        # Entonces si la línea contiene "Apoyo:" la ignoramos como estructura
        if "APOYO:" in t.upper():
            # pero ojo: puede ser "P # 08 Apoyo: ..." (ya capturamos P # 08 arriba solo si era línea limpia)
            # no hacemos nada más.
            continue

        # separar posibles múltiples items en una línea (por comas o ; etc)
        for piece in split_cell_items(t):
            piece = _limpiar_item(piece)
            if not piece:
                continue

            # nos quedamos SOLO con (P)
            if not es_proyectada(piece):
                continue

            # quitar el sufijo (P) para clasificar por prefijo (pero lo conservamos en el string final o no?)
            # Recomendación: conservarlo NO es necesario; para materiales mejor quitar (P).
            code_sin = re.sub(r"\(\s*p\s*\)\s*$", "", piece, flags=re.I).strip()

            col = _clasificar_item(code_sin)
            if col:
                _agregar_en_bucket(bloques[punto_actual], col, code_sin)

    # pasar a DF ANCHO
    rows = [_bucket_to_row(p, b) for p, b in bloques.items()]
    df = pd.DataFrame(rows, columns=COLUMNAS_BASE)

    # limpiar filas vacías (puntos sin nada proyectado)
    if not df.empty:
        cols_no_punto = [c for c in COLUMNAS_BASE if c != "Punto"]
        df = df[df[cols_no_punto].astype(str).apply(lambda r: any(v.strip() for v in r), axis=1)]

    return normalizar_columnas(df, COLUMNAS_BASE)


# -----------------------------------------
# UI Streamlit: modo PDF
# -----------------------------------------
def cargar_desde_pdf_enee() -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    st.subheader("📄 Cargar estructuras desde PDF (ENEE)")

    archivo_pdf = st.file_uploader("Sube el PDF del plano", type=["pdf"], key="upl_pdf_enee")
    if not archivo_pdf:
        return None, None

    # Import local para no forzar dependencia si no está instalada
    try:
        import pdfplumber  # type: ignore
    except Exception:
        st.error("Falta dependencia: pdfplumber. Agrega 'pdfplumber' a requirements.txt")
        return None, None

    # Extraer texto (todas las páginas)
    texto_total = []
    with pdfplumber.open(io.BytesIO(archivo_pdf.getvalue())) as pdf:
        for i, page in enumerate(pdf.pages):
            txt = page.extract_text() or ""
            texto_total.append(txt)

    texto_total = "\n".join(texto_total).strip()
    if not texto_total:
        st.warning("No se detectó texto en el PDF. Si el plano es escaneado (imagen), tocaría OCR.")
        return None, None

    # Parsear a DF ANCHO y mostrar
    df_ancho = extraer_estructuras_desde_texto_pdf(texto_total)

    if df_ancho.empty:
        st.warning("Se leyó el PDF, pero no se encontraron estructuras PROYECTADAS (P).")
        return None, None

    st.success(f"✅ Estructuras proyectadas detectadas: {len(df_ancho)} puntos")
    st.dataframe(df_ancho, use_container_width=True, hide_index=True)

    # Convertir a LARGO y materializar
    ruta_tmp = materializar_df_a_archivo(df_ancho, "pdf")
    df_largo = expand_wide_to_long(df_ancho)

    st.caption("🔎 Vista LARGA (lo que consume el motor)")
    st.dataframe(df_largo, use_container_width=True, hide_index=True)

    return df_largo, ruta_tmp
