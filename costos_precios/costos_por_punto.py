# -*- coding: utf-8 -*-
"""
costos_precios/costos_por_punto.py

Calcula costos por punto a partir de:
- estructuras por punto
- costos unitarios por estructura
"""

from __future__ import annotations
import pandas as pd


def calcular_costos_por_punto(
    df_estructuras_por_punto: pd.DataFrame,
    df_costos_estructuras: pd.DataFrame,
):
    """
    Retorna:
    - df_detalle
    - df_resumen
    """

    # -----------------------------
    # VALIDACIÓN
    # -----------------------------
    if df_estructuras_por_punto is None or df_estructuras_por_punto.empty:
        raise ValueError("df_estructuras_por_punto vacío")

    if df_costos_estructuras is None or df_costos_estructuras.empty:
        raise ValueError("df_costos_estructuras vacío")

    # -----------------------------
    # NORMALIZAR COSTOS
    # -----------------------------
    if "codigodeestructura" not in df_costos_estructuras.columns:
        raise ValueError("df_costos_estructuras debe tener 'codigodeestructura'")

    if "Costo Unitario" not in df_costos_estructuras.columns:
        raise ValueError("df_costos_estructuras debe tener 'Costo Unitario'")

    dict_costos = dict(
        zip(
            df_costos_estructuras["codigodeestructura"].astype(str).str.strip(),
            df_costos_estructuras["Costo Unitario"]
        )
    )

    # -----------------------------
    # CALCULO DETALLE
    # -----------------------------
    resultados = []

    for _, row in df_estructuras_por_punto.iterrows():

        punto = row.get("Punto")
        estructura = str(row.get("codigodeestructura", "")).strip()
        cantidad = float(row.get("Cantidad", 0) or 0)

        precio = dict_costos.get(estructura, 0)
        subtotal = cantidad * precio

        resultados.append({
            "Punto": punto,
            "codigodeestructura": estructura,
            "Cantidad": cantidad,
            "Precio Unitario": precio,
            "Subtotal": subtotal
        })

    df_detalle = pd.DataFrame(resultados)

    # -----------------------------
    # RESUMEN
    # -----------------------------
    df_resumen = (
        df_detalle.groupby("Punto")["Subtotal"]
        .sum()
        .reset_index()
        .rename(columns={"Subtotal": "TOTAL_PUNTO"})
    )

    return df_detalle, df_resumen
