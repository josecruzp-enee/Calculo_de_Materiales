# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd


# =========================================================
# HELPERS
# =========================================================
def _norm(s):
    return str(s or "").strip().upper()


def _validar_df(df: pd.DataFrame, nombre: str):
    if df is None or not isinstance(df, pd.DataFrame):
        raise TypeError(f"{nombre} debe ser DataFrame")

    if df.empty:
        raise ValueError(f"{nombre} está vacío")


def _validar_columnas(df: pd.DataFrame, nombre: str, columnas: list[str]):
    faltantes = [c for c in columnas if c not in df.columns]
    if faltantes:
        raise ValueError(f"{nombre} no tiene columnas requeridas: {faltantes}")


# =========================================================
# MOTOR DE COSTOS POR PUNTO (ALINEADO A CONTRATO)
# =========================================================
def calcular_costos_por_punto(
    df_estructuras_por_punto: pd.DataFrame,
    df_costos_estructuras: pd.DataFrame,
):
    """
    ✔ Dominio puro
    ✔ Contrato consistente con orquestador_costos
    ✔ Validación fuerte

    OUTPUT:
        df_costos_por_punto
        df_resumen_costos_punto
        df_resumen_precios_punto
    """

    # =====================================================
    # VALIDACIÓN BASE
    # =====================================================
    _validar_df(df_estructuras_por_punto, "df_estructuras_por_punto")
    _validar_df(df_costos_estructuras, "df_costos_estructuras")

    _validar_columnas(
        df_estructuras_por_punto,
        "df_estructuras_por_punto",
        ["Punto", "Cantidad"]
    )

    if not ({"Estructura", "CodigoDeEstructura"} & set(df_estructuras_por_punto.columns)):
        raise ValueError("df_estructuras_por_punto debe tener 'Estructura' o 'CodigoDeEstructura'")

    _validar_columnas(
        df_costos_estructuras,
        "df_costos_estructuras",
        ["codigodeestructura", "Precio Unitario"]
    )

    # =====================================================
    # NORMALIZAR COSTOS
    # =====================================================
    df_cost = df_costos_estructuras.copy()

    df_cost["codigodeestructura"] = df_cost["codigodeestructura"].astype(str).map(_norm)
    df_cost["Precio Unitario"] = pd.to_numeric(df_cost["Precio Unitario"], errors="coerce")

    if df_cost["Precio Unitario"].isna().any():
        raise ValueError("Hay precios unitarios inválidos en df_costos_estructuras")

    dict_precios = dict(
        zip(df_cost["codigodeestructura"], df_cost["Precio Unitario"])
    )

    # =====================================================
    # NORMALIZAR ESTRUCTURAS
    # =====================================================
    df_ep = df_estructuras_por_punto.copy()

    col_est = "Estructura" if "Estructura" in df_ep.columns else "CodigoDeEstructura"

    df_ep[col_est] = df_ep[col_est].astype(str).map(_norm)
    df_ep["Cantidad"] = pd.to_numeric(df_ep["Cantidad"], errors="coerce")

    if df_ep["Cantidad"].isna().any():
        raise ValueError("Hay cantidades inválidas en df_estructuras_por_punto")

    if (df_ep["Cantidad"] < 0).any():
        raise ValueError("Hay cantidades negativas en df_estructuras_por_punto")

    # =====================================================
    # CÁLCULO DETALLE (df_costos_por_punto)
    # =====================================================
    filas = []

    for _, row in df_ep.iterrows():

        punto = row["Punto"]
        estructura = row[col_est]
        cantidad = float(row["Cantidad"])

        if not punto:
            raise ValueError("Punto vacío detectado")

        if estructura not in dict_precios:
            raise ValueError(f"Estructura sin precio: {estructura}")

        precio_unit = dict_precios[estructura]
        subtotal = cantidad * precio_unit

        filas.append({
            "Punto": punto,
            "Estructura": estructura,
            "Cantidad": cantidad,
            "Precio Unitario": round(precio_unit, 2),
            "Subtotal Precio": round(subtotal, 2),
        })

    df_costos_por_punto = pd.DataFrame(filas)

    if df_costos_por_punto.empty:
        raise ValueError("No se generaron costos por punto")

    # =====================================================
    # RESUMEN COSTOS
    # =====================================================
    df_resumen_costos_punto = (
        df_costos_por_punto.groupby("Punto")["Subtotal Precio"]
        .sum()
        .reset_index()
        .rename(columns={"Subtotal Precio": "TOTAL_COSTO_PUNTO"})
    )

    # =====================================================
    # RESUMEN PRECIOS (alias)
    # =====================================================
    df_resumen_precios_punto = df_resumen_costos_punto.rename(
        columns={"TOTAL_COSTO_PUNTO": "TOTAL_PRECIO_PUNTO"}
    )

    return (
        df_costos_por_punto,
        df_resumen_costos_punto,
        df_resumen_precios_punto,
    )
