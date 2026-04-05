# -*- coding: utf-8 -*-
# entradas/orquestador_entradas.py

import pandas as pd

from entradas.leer_excel import leer_estructuras
from entradas.leer_tabla import leer_tabla
from entradas.leer_pdf import leer_pdf
from entradas.leer_dxf import leer_dxf

from entradas.normalizar import normalizar_estructuras
from entradas.validacion import validar_estructuras

from entradas.indice_estructuras import cargar_indice_normalizado

from entradas.contratos import EntradaEstructuras


# =========================================================
# ORQUESTADOR GENERAL
# =========================================================

def cargar_entrada(tipo: str, data, ruta_materiales=None) -> EntradaEstructuras:
    """
    Punto único de entrada del sistema.

    tipo:
        - "excel"
        - "tabla"
        - "pdf"
        - "dxf"
        - "ui"

    ruta_materiales:
        ruta al archivo de materiales (para validar contra catálogo)
    """

    log = _get_logger()

    # =========================
    # 1. LECTURA
    # =========================
    if tipo == "excel":
        df = leer_estructuras(data)

    elif tipo == "tabla":
        df = leer_tabla(data)

    elif tipo == "pdf":
        df = leer_pdf(data)

    elif tipo == "dxf":
        df = leer_dxf(data)

    elif tipo == "ui":
        df = _leer_desde_ui(data)

    else:
        raise ValueError(f"Tipo de entrada no soportado: {tipo}")

    # =========================
    # 2. NORMALIZACIÓN 🔥
    # =========================
    df = normalizar_estructuras(df)

    # =========================
    # 3. VALIDACIÓN 🔥 (CON CATÁLOGO)
    # =========================
    if ruta_materiales:
        df_indice = cargar_indice_normalizado(ruta_materiales, log)

        errores, warnings = validar_estructuras(df, df_indice, log)

        if errores:
            raise ValueError(
                "Errores en estructuras:\n" + "\n".join(errores)
            )
    else:
        log("⚠️ No se proporcionó catálogo → validación omitida")

    # =========================
    # 4. SALIDA ESTÁNDAR
    # =========================
    return EntradaEstructuras(df=df, origen=tipo)


# =========================================================
# ADAPTADOR UI
# =========================================================

def _leer_desde_ui(data):

    if isinstance(data, pd.DataFrame):
        return data.copy()

    if isinstance(data, list):
        return pd.DataFrame(data)

    if isinstance(data, dict):
        return pd.DataFrame([data])

    return pd.DataFrame()


# =========================================================
# LOGGER LOCAL
# =========================================================

def _get_logger():
    try:
        import streamlit as st
        return st.write
    except Exception:
        return print
