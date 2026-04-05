# -*- coding: utf-8 -*-
# entradas/orquestador_entradas.py

from __future__ import annotations

from typing import Any
import pandas as pd

# =========================
# LECTURA
# =========================
from entradas.leer_excel import leer_estructuras
from entradas.leer_tabla import leer_tabla
from entradas.leer_pdf import leer_pdf
from entradas.leer_dxf import leer_dxf

# =========================
# PROCESAMIENTO
# =========================
from entradas.normalizar import normalizar_estructuras
from entradas.validacion import validar_estructuras
from entradas.indice_estructuras import cargar_indice_normalizado

# =========================
# MODELO DE SALIDA
# =========================
from materiales.modelos.entrada import EntradaMateriales


# =========================================================
# API PRINCIPAL
# =========================================================

def cargar_entrada(
    tipo: str,
    data: Any,
    *,
    tension: float,
    df_cables: pd.DataFrame | None = None,
    ruta_materiales: str | None = None,
    permitir_sin_catalogo: bool = False,
) -> EntradaMateriales:
    """
    Orquestador de entradas.

    Flujo:
        1. Leer
        2. Normalizar
        3. Validar
        4. Transformar → estructuras_por_punto
        5. Salida → EntradaMateriales
    """

    log = _get_logger()

    # =====================================================
    # 1. LECTURA
    # =====================================================
    df = _leer_por_tipo(tipo, data)

    if df is None or df.empty:
        raise ValueError("No se pudo leer información válida de la entrada")

    log(f"✔ Lectura completada: {len(df)} filas")

    # =====================================================
    # 2. NORMALIZACIÓN
    # =====================================================
    try:
        df = normalizar_estructuras(df)
    except Exception as e:
        raise ValueError(f"Error en normalización ({tipo}): {str(e)}")

    if df is None or df.empty:
        raise ValueError("La normalización generó un DataFrame vacío")

    log("✔ Normalización completada")

    # =====================================================
    # 3. VALIDACIÓN
    # =====================================================
    errores = []
    warnings = []

    if ruta_materiales and not permitir_sin_catalogo:
        df_indice = cargar_indice_normalizado(ruta_materiales, log)
        df, errores, warnings = validar_estructuras(df, df_indice, log)

        log(f"✔ Validación completada | warnings: {len(warnings)}")

    if errores:
        raise ValueError("Errores en estructuras:\n" + "\n".join(errores))

    # =====================================================
    # 4. TRANSFORMACIÓN
    # =====================================================
    estructuras_por_punto = _convertir_df_a_por_punto(df)

    # =====================================================
    # 5. SALIDA (🔥 ALINEADO A MATERIALES)
    # =====================================================
    return EntradaMateriales(
        estructuras_por_punto=estructuras_por_punto,
        tension=tension,
        df_cables=df_cables,
    )


# =========================================================
# LECTOR CENTRALIZADO
# =========================================================

def _leer_por_tipo(tipo: str, data) -> pd.DataFrame:

    if tipo == "excel":
        return leer_estructuras(data)

    elif tipo == "tabla":
        return leer_tabla(data)

    elif tipo == "pdf":
        return leer_pdf(data)

    elif tipo == "dxf":
        return leer_dxf(data)

    elif tipo == "ui":
        return _leer_desde_ui(data)

    raise ValueError(f"Tipo de entrada no soportado: {tipo}")


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
# TRANSFORMACIÓN CLAVE
# =========================================================

def _convertir_df_a_por_punto(df: pd.DataFrame):

    resultado = {}

    for _, row in df.iterrows():

        punto = str(row.get("Punto", "")).strip()
        estructura = str(row.get("codigodeestructura", "")).strip().upper()

        if not punto or not estructura:
            continue

        if punto not in resultado:
            resultado[punto] = []

        resultado[punto].append(estructura)

    return resultado


# =========================================================
# LOGGER SIMPLE
# =========================================================

def _get_logger():
    def _log(msg):
        print(msg)
    return _log
