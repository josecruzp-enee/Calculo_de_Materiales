# -*- coding: utf-8 -*-
# interfaz/estructuras.py

from __future__ import annotations
from typing import Tuple, Optional
import traceback

import pandas as pd
import streamlit as st

from core.transformador_estructuras import coerce_df_estructuras_largo
from interfaz.estructuras_comunes import expand_wide_to_long, materializar_df_a_archivo

# fuentes
from interfaz.estructuras_desplegables import listas_desplegables
from interfaz.estructuras_dxf_enee import extraer_estructuras_desde_dxf, leer_dxf_streamlit
from interfaz.estructuras_pdf_enee import cargar_desde_pdf_enee


# =========================================================
# FUENTES DE DATOS (ANCHO)
# =========================================================

def cargar_desde_excel_ancho() -> Optional[pd.DataFrame]:
    archivo = st.file_uploader("Archivo de estructuras (.xlsx)", type=["xlsx"], key="upl_estructuras")

    if not archivo:
        return None

    try:
        xls = pd.ExcelFile(archivo)
        hoja = next(
            (s for s in xls.sheet_names if s.strip().lower() == "estructuras"),
            xls.sheet_names[0]
        )
        return pd.read_excel(xls, sheet_name=hoja)

    except Exception as e:
        st.error(f"Error leyendo el Excel: {e}")
        return None


def pegar_tabla_ancho() -> Optional[pd.DataFrame]:
    from interfaz.estructuras_comunes import parsear_texto_a_df, COLUMNAS_BASE

    texto = st.text_area(
        "Pega aquí tu tabla (CSV/TSV).",
        height=200,
        key="txt_pegar_tabla",
    )

    if not texto:
        return None

    df = parsear_texto_a_df(texto, COLUMNAS_BASE)
    return df if df is not None and not df.empty else None


def cargar_pdf_ancho() -> Optional[pd.DataFrame]:
    try:
        return cargar_desde_pdf_enee()
    except Exception:
        st.error("❌ No se pudo cargar el lector PDF ENEE.")
        st.code(traceback.format_exc())
        return None


def cargar_dxf_ancho() -> Optional[pd.DataFrame]:
    st.subheader("📐 Cargar estructuras desde DXF (ENEE)")

    archivo = st.file_uploader("Sube el DXF del plano", type=["dxf"], key="upl_dxf")

    if not archivo:
        return None

    capa = st.text_input(
        "Capa de estructuras (opcional)",
        value="Estructuras",
        key="capa_estructuras_dxf"
    ).strip()

    try:
        doc = leer_dxf_streamlit(archivo)
        df_ancho = extraer_estructuras_desde_dxf(
            doc,
            capa_objetivo=capa if capa else ""
        )
        return df_ancho if df_ancho is not None and not df_ancho.empty else None

    except Exception:
        st.error("💥 ERROR REAL DXF:")
        st.code(traceback.format_exc())
        return None


# =========================================================
# DISPATCHER INTERNO (TEMPORAL)
# =========================================================

def _obtener_df_ancho_por_modo(modo: str) -> Optional[pd.DataFrame]:

    if modo == "excel":
        return cargar_desde_excel_ancho()

    elif modo == "tabla":
        return pegar_tabla_ancho()

    elif modo == "pdf":
        return cargar_pdf_ancho()

    elif modo == "dxf":
        return cargar_dxf_ancho()

    return None


# =========================================================
# SECCIÓN PRINCIPAL
# =========================================================

def seccion_entrada_estructuras(modo_carga: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:

    modo = (modo_carga or "").strip().lower()

    # =====================================================
    # CASO: DESPLEGABLES (YA VIENE EN FORMATO LARGO)
    # =====================================================

    if modo == "manual":

        df_largo, ruta_tmp = listas_desplegables()

        if df_largo is None or df_largo.empty:
            return None, None

        ruta_tmp = ruta_tmp or materializar_df_a_archivo(df_largo, etiqueta=modo)

        return df_largo, ruta_tmp

    # =====================================================
    # RESTO DE MODOS (ANCHO)
    # =====================================================

    df_ancho = _obtener_df_ancho_por_modo(modo)

    if df_ancho is None or df_ancho.empty:
        return None, None

    # =====================================================
    # TRANSFORMACIÓN (ANCHO → LARGO)
    # =====================================================

    if modo == "dxf":
        # DXF viene más limpio
        df_largo = expand_wide_to_long(df_ancho)
    else:
        df_largo = coerce_df_estructuras_largo(df_ancho)

    if df_largo is None or df_largo.empty:
        st.error("No pude convertir estructuras a formato largo (Punto, codigodeestructura, cantidad).")
        st.write("Columnas recibidas:", list(df_ancho.columns))
        st.dataframe(df_ancho.head(10))
        return None, None

    # =====================================================
    # SALIDA
    # =====================================================

    ruta_tmp = materializar_df_a_archivo(df_largo, etiqueta=modo)

    return df_largo, ruta_tmp
