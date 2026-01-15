# interfaz/estructuras.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Tuple, Optional, List, Dict
import io
import os
import re
import time
import tempfile

import pandas as pd
import streamlit as st


# =============================================================================
# Esquema base (ANCHO) que ve el usuario en la UI
# =============================================================================
COLUMNAS_BASE: List[str] = [
    "Punto",
    "Poste",
    "Primario",
    "Secundario",
    "Retenidas",
    "Conexiones a tierra",
    "Transformadores",
    "Luminarias",
]


# =============================================================================
# Utilidades comunes
# =============================================================================
def _normalizar_columnas(df: pd.DataFrame, columnas: List[str]) -> pd.DataFrame:
    """Asegura todas las columnas requeridas en orden ANCHO y renombra variantes comunes."""
    df = df.copy()
    df = df.rename(columns={
        "Retenida": "Retenidas",
        "Aterrizaje": "Conexiones a tierra",
        "Transformador": "Transformadores",
    })
    for c in columnas:
        if c not in df.columns:
            df[c] = ""
    return df[columnas]


def _norm_code_value(s: str) -> str:
    """Limpia código de estructura: recorta y quita sufijos finales '(E)/(P)/(R)'."""
    if pd.isna(s):
        return ""
    s = str(s).strip()
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s).strip()
    return s


def _split_cell_items(cell: str) -> List[str]:
    """Separa una celda por coma, punto y coma o saltos de línea."""
    if not isinstance(cell, str):
        return []
    s = cell.strip().strip('"').strip("'")
    if not s or s == "-":
        return []
    parts = re.split(r'[,;\n\r]+', s)
    return [p.strip() for p in parts if p.strip()]


def _parse_item(piece: str) -> Tuple[str, int]:
    """
    Interpreta cantidad + código. Soporta:
      - '2× R-1' / '2x R-1'
      - '2 R-1'
      - '2B-I-4'  (cantidad pegada al código)
      - 'A-I-4 (E)' (cantidad implícita 1)
    """
    m = re.match(r'^(\d+)\s*[x×]\s*(.+)$', piece, flags=re.I)  # 2x CODE
    if m:
        return _norm_code_value(m.group(2)), int(m.group(1))
    m = re.match(r'^(\d+)\s+(.+)$', piece)  # 2 CODE
    if m:
        return _norm_code_value(m.group(2)), int(m.group(1))
    m = re.match(r'^(\d+)([A-Za-z].+)$', piece)  # 2CODE
    if m:
        return _norm_code_value(m.group(2)), int(m.group(1))
    return _norm_code_value(piece), 1


def _expand_wide_to_long(df_ancho: pd.DataFrame) -> pd.DataFrame:
    """ANCHO -> LARGO para el motor de reportes."""
    df = _normalizar_columnas(df_ancho, COLUMNAS_BASE).copy()
    cat_cols = [
        "Poste", "Primario", "Secundario", "Retenidas",
        "Conexiones a tierra", "Transformadores", "Luminarias"
    ]
    rows = []
    for _, r in df.iterrows():
        punto = str(r.get("Punto", "")).strip()
        for col in cat_cols:
            for piece in _split_cell_items(str(r.get(col, "") or "")):
                code, qty = _parse_item(piece)
                if code:
                    rows.append({
                        "Punto": punto,
                        "codigodeestructura": code,
                        "cantidad": int(qty),
                    })
    return pd.DataFrame(rows, columns=["Punto", "codigodeestructura", "cantidad"])


def _materializar_df_a_archivo(df_ancho: pd.DataFrame, etiqueta: str = "data") -> str:
    """
    Crea un .xlsx temporal con:
      - Hoja 'estructuras' (LARGO) primero
      - Hoja 'estructuras_ancha' (ANCHO) auxiliar
    """
    ts = int(time.time())
    ruta = os.path.join(tempfile.gettempdir(), f"estructuras_{etiqueta}_{ts}.xlsx")

    df_ancho_norm = _normalizar_columnas(df_ancho, COLUMNAS_BASE)
    df_largo = _expand_wide_to_long(df_ancho_norm)

    try:
        writer = pd.ExcelWriter(ruta, engine="openpyxl")
    except Exception:
        writer = pd.ExcelWriter(ruta, engine="xlsxwriter")

    with writer:
        df_largo.to_excel(writer, sheet_name="estructuras", index=False)
        df_ancho_norm.to_excel(writer, sheet_name="estructuras_ancha", index=False)

    # Debug útil (opcional)
    try:
        xls = pd.ExcelFile(ruta)
        hoja = next((s for s in xls.sheet_names if s.lower() == "estructuras"), xls.sheet_names[0])
        cols = list(pd.read_excel(xls, sheet_name=hoja, nrows=0).columns)
        st.caption("🔎 Estructuras generadas (debug)")
        st.write({"ruta": ruta, "hojas": xls.sheet_names, "columnas_estructuras": cols})
    except Exception:
        pass

    return ruta


# =============================================================================
# Modo: Excel
# =============================================================================
def _parsear_texto_a_df(texto: str, columnas: List[str]) -> pd.DataFrame:
    """Convierte texto pegado (CSV/TSV/; o | o whitespace) a DataFrame ANCHO."""
    txt = (texto or "").strip()
    if not txt:
        return pd.DataFrame(columns=columnas)

    df = None
    for sep in ("\t", ",", ";", "|"):
        try:
            df = pd.read_csv(io.StringIO(txt), sep=sep)
            break
        except Exception:
            df = None

    if df is None:
        try:
            df = pd.read_csv(io.StringIO(txt), delim_whitespace=True)
        except Exception:
            return pd.DataFrame(columns=columnas)

    return _normalizar_columnas(df, columnas)


def cargar_desde_excel() -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    archivo = st.file_uploader("Archivo de estructuras (.xlsx)", type=["xlsx"], key="upl_estructuras")
    if not archivo:
        return None, None

    try:
        xls = pd.ExcelFile(archivo)
        hoja = next((s for s in xls.sheet_names if s.strip().lower() == "estructuras"), xls.sheet_names[0])
        df_ancho = pd.read_excel(xls, sheet_name=hoja)
    except Exception as e:
        st.error(f"Error leyendo el Excel: {e}")
        return None, None

    df_ancho = _normalizar_columnas(df_ancho, COLUMNAS_BASE)
    ruta_tmp = _materializar_df_a_archivo(df_ancho, "excel")
    df_largo = _expand_wide_to_long(df_ancho)
    st.success(f"✅ Cargadas {len(df_largo)} filas (largo) desde Excel")
    return df_largo, ruta_tmp


# =============================================================================
# Modo: Pegar tabla
# =============================================================================
def pegar_tabla() -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    texto_pegado = st.text_area(
        "Pega aquí tu tabla (CSV/TSV). Soporta coma y saltos de línea en celdas.",
        height=200,
        key="txt_pegar_tabla",
    )
    if not texto_pegado:
        return None, None

    df_ancho = _parsear_texto_a_df(texto_pegado, COLUMNAS_BASE)
    if df_ancho is None or df_ancho.empty:
        st.warning("No se detectaron filas válidas en el texto.")
        return None, None

    ruta_tmp = _materializar_df_a_archivo(df_ancho, "pega")
    df_largo = _expand_wide_to_long(df_ancho)
    st.success(f"✅ Tabla pegada convertida ({len(df_largo)} filas)")
    return df_largo, ruta_tmp


# =============================================================================
# Modo: PDF (stub por ahora)
# =============================================================================
def cargar_desde_pdf_enee() -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    st.subheader("📄 Cargar estructuras desde PDF (ENEE)")

    archivo_pdf = st.file_uploader("Sube el PDF del plano", type=["pdf"], key="upl_pdf_enee")
    if not archivo_pdf:
        return None, None

    st.success(f"✅ PDF cargado: {archivo_pdf.name}")
    st.write({"tamaño_bytes": archivo_pdf.size, "tipo": archivo_pdf.type})

    # TODO: extractor real -> df_ancho -> df_largo + ruta_tmp
    return None, None


# =============================================================================
# IMPORT AL FINAL para evitar circular import
# =============================================================================
from interfaz.estructuras_desplegables import listas_desplegables  # noqa: E402


# =============================================================================
# Router público
# =============================================================================
def seccion_entrada_estructuras(modo_carga: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    modo_raw = (modo_carga or "").strip().lower()

    mapa = {
        "desde archivo excel": "excel",
        "excel": "excel",
        "pegar tabla": "pegar",
        "pegar": "pegar",
        "listas desplegables": "desplegables",
        "desplegables": "desplegables",
        "pdf": "pdf",
        "subir pdf (enee)": "pdf",
    }

    modo = mapa.get(modo_raw, "desplegables")

    if modo == "excel":
        return cargar_desde_excel()

    if modo == "pegar":
        return pegar_tabla()

    if modo == "pdf":
        return cargar_desde_pdf_enee()

    return listas_desplegables()
