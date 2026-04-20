# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from typing import Tuple

# 🔥 IMPORT DIRECTO DE TU BIBLIOTECA
from costos_precios.precios_estructura import PRECIOS_BIBLIOTECA


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================
def calcular_precios_por_punto(
    df_estructuras_por_punto: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Calcula el PRECIO por punto basado en la biblioteca de precios.

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

    # =====================================================
    # NORMALIZACIÓN
    # =====================================================
    df = df_estructuras_por_punto.copy()

    df["Punto"] = df["Punto"].astype(str).str.strip()
    df["codigodeestructura"] = df["codigodeestructura"].astype(str).str.strip().str.upper()
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)

    df = df[df["Cantidad"] > 0]

    if df.empty:
        raise ValueError("No hay estructuras con cantidad válida")

    # =====================================================
    # VALIDACIÓN DE BIBLIOTECA
    # =====================================================
    estructuras_unicas = set(df["codigodeestructura"])
    estructuras_catalogo = set(PRECIOS_BIBLIOTECA.keys())

    faltantes = estructuras_unicas - estructuras_catalogo

    if faltantes:
        raise ValueError(f"Estructuras sin precio en biblioteca: {sorted(faltantes)}")

    # =====================================================
    # ASIGNACIÓN DE PRECIOS
    # =====================================================
    df["Precio Unitario"] = df["codigodeestructura"].map(PRECIOS_BIBLIOTECA)

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

    df_detalle = df_detalle.sort_values(
        ["Punto", "codigodeestructura"]
    ).reset_index(drop=True)

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
