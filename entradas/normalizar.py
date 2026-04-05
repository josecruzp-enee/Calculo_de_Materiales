# -*- coding: utf-8 -*-
"""
normalizar.py

Wrapper oficial del sistema para normalizar estructuras.
"""

import pandas as pd

from entradas.normalizacion_estructuras import (
    limpiar_df_estructuras,
    construir_estructuras_por_punto_y_conteo,
)


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================

def normalizar_estructuras(df: pd.DataFrame) -> pd.DataFrame:
    """
    Entrada: cualquier formato (Excel, PDF, DXF, UI, tabla)

    Salida:
        DataFrame con columnas:
        Punto | codigodeestructura | cantidad
    """

    if df is None or df.empty:
        return pd.DataFrame(columns=["Punto", "codigodeestructura", "cantidad"])

    df = df.copy()

    # =====================================================
    # CASO 1: YA VIENE EN FORMATO LARGO
    # =====================================================
    if "codigodeestructura" in df.columns:

        if "Punto" not in df.columns and "punto" in df.columns:
            df.rename(columns={"punto": "Punto"}, inplace=True)

        if "cantidad" not in df.columns:
            df["cantidad"] = 1

        df_limpio = limpiar_df_estructuras(df)

        _, _, df_final = construir_estructuras_por_punto_y_conteo(df_limpio)

        return df_final

    # =====================================================
    # CASO 2: FORMATO ANCHO
    # =====================================================
    df_largo = _convertir_a_largo(df)

    df_limpio = limpiar_df_estructuras(df_largo)

    _, _, df_final = construir_estructuras_por_punto_y_conteo(df_limpio)

    return df_final


# =========================================================
# CONVERSIÓN A FORMATO LARGO
# =========================================================

def _convertir_a_largo(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # detectar columna punto
    col_punto = None
    for c in df.columns:
        if "punto" in c.lower():
            col_punto = c
            break

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

    return pd.DataFrame(filas)
