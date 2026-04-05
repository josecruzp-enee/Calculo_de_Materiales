# -*- coding: utf-8 -*-
"""
normalizar.py
Fachada de normalización de estructuras (clean + producción)
"""

import pandas as pd

from entradas.normalizacion_estructuras import (
    construir_estructuras_por_punto_y_conteo,
)


# =========================================================
# API PRINCIPAL
# =========================================================
def normalizar_estructuras(df: pd.DataFrame):
    """
    Pipeline completo de normalización.

    Entrada:
        df (cualquier formato)

    Salida:
        df_normalizado
        errores
        warnings
    """

    if df is None or df.empty:
        return (
            pd.DataFrame(columns=["Punto", "codigodeestructura", "cantidad"]),
            ["Entrada vacía"],
            []
        )

    df = df.copy()

    # =====================================================
    # 1. ASEGURAR FORMATO LARGO
    # =====================================================
    df_base = _asegurar_formato_largo(df)

    # =====================================================
    # 2. MOTOR DE NORMALIZACIÓN
    # =====================================================
    _, _, df_final, errores, warnings = \
        construir_estructuras_por_punto_y_conteo(df_base)

    return df_final, errores, warnings


# =========================================================
# FORMATO
# =========================================================
def _asegurar_formato_largo(df: pd.DataFrame) -> pd.DataFrame:
    """
    Garantiza que el DataFrame esté en formato largo.
    """

    if _es_formato_largo(df):
        return df.copy()

    return _convertir_a_largo(df)


def _es_formato_largo(df: pd.DataFrame) -> bool:
    cols = [c.lower() for c in df.columns]

    return (
        "codigodeestructura" in cols
        and any("punto" in c for c in cols)
    )


# =========================================================
# CONVERSIÓN A FORMATO LARGO
# =========================================================
def _convertir_a_largo(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    col_punto = None

    for c in df.columns:
        if "punto" in c.lower():
            col_punto = c
            break

    # Si no existe punto → generar
    if col_punto is None:
        df["Punto"] = [f"P{i+1}" for i in range(len(df))]
        col_punto = "Punto"

    filas = []

    for _, row in df.iterrows():

        punto = row[col_punto]

        for col in df.columns:

            if col == col_punto:
                continue

            valor = row[col]

            if pd.isna(valor):
                continue

            texto = str(valor).strip()

            if not texto:
                continue

            filas.append({
                "Punto": punto,
                "codigodeestructura": texto,
                "cantidad": 1
            })

    return pd.DataFrame(
        filas,
        columns=["Punto", "codigodeestructura", "cantidad"]
    )
