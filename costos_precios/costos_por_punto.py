# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd


def calcular_costos_por_punto(
    df_estructuras_por_punto: pd.DataFrame,
    df_costos_estructuras: pd.DataFrame,
):
    """
    Retorna:
    - df_detalle
    - df_resumen_costos
    - df_resumen_precios
    """

    # =====================================================
    # VALIDACIÓN INPUT
    # =====================================================
    if not isinstance(df_estructuras_por_punto, pd.DataFrame) or df_estructuras_por_punto.empty:
        raise ValueError("df_estructuras_por_punto inválido o vacío")

    if not isinstance(df_costos_estructuras, pd.DataFrame) or df_costos_estructuras.empty:
        raise ValueError("df_costos_estructuras inválido o vacío")

    required_ep = {"Punto", "codigodeestructura", "Cantidad"}
    if not required_ep.issubset(df_estructuras_por_punto.columns):
        raise ValueError(f"df_estructuras_por_punto debe tener {required_ep}")

    required_ce = {"codigodeestructura", "Costo Unitario"}
    if not required_ce.issubset(df_costos_estructuras.columns):
        raise ValueError(f"df_costos_estructuras debe tener {required_ce}")

    # =====================================================
    # NORMALIZACIÓN
    # =====================================================
    df_ep = df_estructuras_por_punto.copy()
    df_ce = df_costos_estructuras.copy()

    df_ep["codigodeestructura"] = df_ep["codigodeestructura"].astype(str).str.strip().str.upper()
    df_ce["codigodeestructura"] = df_ce["codigodeestructura"].astype(str).str.strip().str.upper()

    df_ep["Punto"] = df_ep["Punto"].astype(str).str.strip()

    df_ep["Cantidad"] = pd.to_numeric(df_ep["Cantidad"], errors="coerce").fillna(0)

    df_ce["Costo Unitario"] = pd.to_numeric(df_ce["Costo Unitario"], errors="coerce")
    df_ce["Precio Unitario"] = pd.to_numeric(df_ce["Precio Unitario"], errors="coerce")

    # =====================================================
    # LIMPIEZA
    # =====================================================
    df_ep = df_ep[df_ep["Cantidad"] > 0]

    if df_ep.empty:
        raise ValueError("df_estructuras_por_punto sin cantidades válidas")

    # 🔥 VALIDACIÓN FUERTE (NO SILENCIOSA)
    if df_ce["codigodeestructura"].duplicated().any():
        dup = df_ce[df_ce["codigodeestructura"].duplicated()]["codigodeestructura"].unique()
        raise ValueError(f"Estructuras duplicadas en costos: {list(dup)}")

    # validar valores
    if (df_ce["Costo Unitario"] <= 0).any():
        raise ValueError("Hay costos unitarios <= 0")

    if (df_ce["Precio Unitario"] <= 0).any():
        raise ValueError("Hay precios unitarios <= 0")

    # =====================================================
    # MERGE CONTROLADO
    # =====================================================
    df = df_ep.merge(
        df_ce,
        on="codigodeestructura",
        how="left",
        validate="many_to_one",
    )

    # =====================================================
    # VALIDACIÓN CRÍTICA
    # =====================================================
    if df["Costo Unitario"].isna().any():
        faltantes = df.loc[df["Costo Unitario"].isna(), "codigodeestructura"].unique()
        raise ValueError(f"Estructuras sin costo definido: {list(faltantes)}")

    if df["Precio Unitario"].isna().any():
        faltantes = df.loc[df["Precio Unitario"].isna(), "codigodeestructura"].unique()
        raise ValueError(f"Estructuras sin precio definido: {list(faltantes)}")

    # =====================================================
    # CÁLCULOS
    # =====================================================
    df["Subtotal Costo"] = (df["Cantidad"] * df["Costo Unitario"]).round(2)
    df["Subtotal Precio"] = (df["Cantidad"] * df["Precio Unitario"]).round(2)

    # =====================================================
    # DETALLE
    # =====================================================
    df_detalle = df[
        [
            "Punto",
            "codigodeestructura",
            "Cantidad",
            "Costo Unitario",
            "Precio Unitario",
            "Subtotal Costo",
            "Subtotal Precio",
        ]
    ].copy()

    df_detalle = df_detalle.sort_values(["Punto", "codigodeestructura"]).reset_index(drop=True)

    # =====================================================
    # RESUMEN COSTOS
    # =====================================================
    df_resumen_costos = (
        df_detalle.groupby("Punto", as_index=False)["Subtotal Costo"]
        .sum()
        .rename(columns={"Subtotal Costo": "TOTAL_COSTO_PUNTO"})
        .sort_values("Punto")
        .reset_index(drop=True)
    )

    # =====================================================
    # RESUMEN PRECIOS
    # =====================================================
    df_resumen_precios = (
        df_detalle.groupby("Punto", as_index=False)["Subtotal Precio"]
        .sum()
        .rename(columns={"Subtotal Precio": "TOTAL_PRECIO_PUNTO"})
        .sort_values("Punto")
        .reset_index(drop=True)
    )

    return df_detalle, df_resumen_costos, df_resumen_precios
