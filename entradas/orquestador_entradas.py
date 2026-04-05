# -*- coding: utf-8 -*-
# entradas/orquestador_entradas.py

import pandas as pd

from entradas.leer_excel import leer_estructuras
from entradas.leer_tabla import leer_tabla
# from entradas.leer_dxf import leer_dxf  # cuando lo tengas

from entradas.normalizar import normalizar_estructuras
from entradas.validar import validar_estructuras

from entradas.contratos import EntradaEstructuras


# =========================================================
# ORQUESTADOR GENERAL
# =========================================================

def cargar_entrada(tipo: str, data) -> EntradaEstructuras:
    """
    Punto único de entrada del sistema.

    tipo:
        - "excel"
        - "tabla"
        - "dxf"
        - "ui"
    """

    # =========================
    # 1. LECTURA
    # =========================
    if tipo == "excel":
        df = leer_estructuras(data)

    elif tipo == "tabla":
        df = leer_tabla(data)

    # elif tipo == "dxf":
    #     df = leer_dxf(data)

    elif tipo == "ui":
        df = _leer_desde_ui(data)

    else:
        raise ValueError(f"Tipo de entrada no soportado: {tipo}")

    # =========================
    # 2. NORMALIZACIÓN 🔥
    # =========================
    df = normalizar_estructuras(df)

    # =========================
    # 3. VALIDACIÓN
    # =========================
    validar_estructuras(df)

    # =========================
    # 4. SALIDA ESTÁNDAR
    # =========================
    return EntradaEstructuras(df=df, origen=tipo)


# =========================================================
# ADAPTADOR UI
# =========================================================

def _leer_desde_ui(data):
    """
    Convierte datos de interfaz en DataFrame.
    """

    if isinstance(data, pd.DataFrame):
        return data.copy()

    if isinstance(data, list):
        return pd.DataFrame(data)

    if isinstance(data, dict):
        return pd.DataFrame([data])

    return pd.DataFrame()
