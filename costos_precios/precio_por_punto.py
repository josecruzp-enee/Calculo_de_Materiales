# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from costos_precios.precios_estructura import PRECIOS_BIBLIOTECA


def calcular_precios_por_punto(
    df_estructuras_por_punto: pd.DataFrame,
):
    """
    Calcula PRECIOS por punto usando biblioteca de estructuras.

    Retorna:
    - df_detalle
    - df_resumen_precios
    """

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    if not isinstance(df_estructuras_por_punto, pd.DataFrame) or df_estructuras_por_punto.empty:
        raise ValueError("df_estructuras_por_punto inválido o vacío")

    required = {"Punto", "codigodeestructura", "Cantidad"}
    if not required.issubset(df_estructuras_por_punto.columns):
        raise ValueError(f"df_estructuras_por_punto debe tener {required}")

    df = df_estructuras_por_punto.copy()

    # =====================================================
    # NORMALIZACIÓN
    # =====================================================
    df["codigodeestructura"] = df["codigodeestructura"].astype(str).str.strip().str.upper()
    df["Punto"] = df["Punto"].astype(str).str.strip()
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)

    df = df[df["Cantidad"] > 0]

    if df.empty:
        raise ValueError("No hay estructuras con cantidad válida")

    # =====================================================
    # MAPEO DE PRECIOS (BIBLIOTECA)
    # =====================================================
    def obtener_precio(estructura: str) -> float:
        if estructura not in PRECIOS_BIBLIOTECA:
            raise ValueError(f"Estructura sin precio en biblioteca: {estructura}")
        return PRECIOS_BIBLIOTECA[estructura]

    df["Precio Unitario"] = df["codigodeestructura"].apply(obtener_precio)

    # =====================================================
    # CÁLCULOS
    # =====================================================
    df["Subtotal Precio"] = (df["Cantidad"] * df["Precio Unitario"]).round(2)

    # =====================================================
    # DETALLE
    # =====================================================
    df_detalle = df[
        [
            "Punto",
            "codigodeestructura",
            "Cantidad",
            "Precio Unitario",
            "Subtotal Precio",
        ]
    ].copy()

    df_detalle = df_detalle.sort_values(["Punto", "codigodeestructura"]).reset_index(drop=True)

    # =====================================================
    # RESUMEN POR PUNTO
    # =====================================================
    df_resumen_precios = (
        df_detalle.groupby("Punto", as_index=False)["Subtotal Precio"]
        .sum()
        .rename(columns={"Subtotal Precio": "TOTAL_PRECIO_PUNTO"})
        .sort_values("Punto")
        .reset_index(drop=True)
    )

    return df_detalle, df_resumen_precios
