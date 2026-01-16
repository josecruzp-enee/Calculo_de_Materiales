# interfaz/estructuras.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Tuple, Optional
import traceback

import pandas as pd
import streamlit as st

from interfaz.estructuras_comunes import (
    COLUMNAS_BASE,
    normalizar_columnas,
    expand_wide_to_long,
    materializar_df_a_archivo,
    parsear_texto_a_df,
)

# ✅ Desplegables (sin circular)
from interfaz.estructuras_desplegables import listas_desplegables
from interfaz.estructuras_dxf_enee import cargar_desde_dxf_enee
from interfaz.estructuras_pdf_enee import cargar_desde_pdf_enee


# =============================================================================
# Modo: Excel
# =============================================================================
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

    df_ancho = normalizar_columnas(df_ancho, COLUMNAS_BASE)
    ruta_tmp = materializar_df_a_archivo(df_ancho, "excel")
    df_largo = expand_wide_to_long(df_ancho)

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

    df_ancho = parsear_texto_a_df(texto_pegado, COLUMNAS_BASE)
    if df_ancho is None or df_ancho.empty:
        st.warning("No se detectaron filas válidas en el texto.")
        return None, None

    ruta_tmp = materializar_df_a_archivo(df_ancho, "pega")
    df_largo = expand_wide_to_long(df_ancho)

    st.success(f"✅ Tabla pegada convertida ({len(df_largo)} filas)")
    return df_largo, ruta_tmp


# =============================================================================
# Modo: PDF (ENEE) - import tardío para evitar caídas al iniciar
# =============================================================================
def cargar_desde_pdf_router() -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Import tardío para evitar que la app se caiga al arrancar por:
    - errores de dependencias
    - errores de sintaxis por versión de Python
    - cambios en el módulo PDF
    """
    try:
        from interfaz.estructuras_pdf_enee import cargar_desde_pdf_enee
        return cargar_desde_pdf_enee()
    except Exception:
        st.error("❌ No se pudo cargar el lector PDF ENEE.")
        st.code(traceback.format_exc())
        return None, None


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
        "pdf (enee)": "pdf",

        # ✅ DXF
        "dxf": "dxf",
        "dxf (enee)": "dxf",
    }

    modo = mapa.get(modo_raw, "desplegables")

    if modo == "excel":
        return cargar_desde_excel()

    if modo == "pegar":
        return pegar_tabla()

    if modo == "pdf":
        return cargar_desde_pdf_router()

    if modo == "dxf":
        return cargar_desde_dxf_enee()
        
    # por defecto
    return listas_desplegables()

