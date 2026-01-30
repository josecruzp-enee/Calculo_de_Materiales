# interfaz/estructuras.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Tuple, Optional
import traceback

import pandas as pd
import streamlit as st

from modulo.entradas.transformador_estructuras import convertir_ancho_a_largo

# fuentes
from interfaz.estructuras_desplegables import listas_desplegables  # debe devolver df_ancho
from interfaz.estructuras_dxf_enee import extraer_estructuras_desde_dxf, leer_dxf_streamlit  # o tu función pública
from interfaz.estructuras_pdf_enee import cargar_desde_pdf_enee  # ideal: que devuelva df_ancho


def cargar_desde_excel_ancho() -> Optional[pd.DataFrame]:
    archivo = st.file_uploader("Archivo de estructuras (.xlsx)", type=["xlsx"], key="upl_estructuras")
    if not archivo:
        return None
    try:
        xls = pd.ExcelFile(archivo)
        hoja = next((s for s in xls.sheet_names if s.strip().lower() == "estructuras"), xls.sheet_names[0])
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
        return cargar_desde_pdf_enee()  # ideal: que retorne df_ancho
    except Exception:
        st.error("❌ No se pudo cargar el lector PDF ENEE.")
        st.code(traceback.format_exc())
        return None


def cargar_dxf_ancho() -> Optional[pd.DataFrame]:
    st.subheader("📐 Cargar estructuras desde DXF (ENEE)")
    archivo = st.file_uploader("Sube el DXF del plano", type=["dxf"], key="upl_dxf")
    if not archivo:
        return None

    capa = st.text_input("Capa de estructuras (opcional)", value="Estructuras", key="capa_estructuras_dxf").strip()

    try:
        doc = leer_dxf_streamlit(archivo)
        df_ancho = extraer_estructuras_desde_dxf(doc, capa_objetivo=capa if capa else "")
        return df_ancho if df_ancho is not None and not df_ancho.empty else None
    except Exception as e:
        st.error(f"No pude leer el DXF: {e}")
        return None


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
        "dxf": "dxf",
        "dxf (enee)": "dxf",
    }

    modo = mapa.get(modo_raw, "desplegables")

    # 1) obtener ANCHO según fuente
    if modo == "excel":
        df_ancho = cargar_desde_excel_ancho()

    elif modo == "pegar":
        df_ancho = pegar_tabla_ancho()

    elif modo == "pdf":
        df_ancho = cargar_pdf_ancho()

    elif modo == "dxf":
        df_ancho = cargar_dxf_ancho()

    else:
        df_ancho = listas_desplegables()  # importante: que esto devuelva df_ancho

    if df_ancho is None or df_ancho.empty:
        return None, None

    # 2) convertir ANCHO → LARGO (único camino)
    _, df_largo, ruta_tmp = convertir_ancho_a_largo(df_ancho, etiqueta=modo)

    return df_largo, ruta_tmp
