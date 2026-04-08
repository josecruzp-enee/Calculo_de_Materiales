# -*- coding: utf-8 -*-
from __future__ import annotations
import pandas as pd

from materiales.calculos.materiales_puntos import calcular_materiales_por_punto
from ayuda.debug import debug_guardar

COLUMNAS_STD = ["Materiales", "Unidad", "Cantidad"]


# =========================================================
# VALIDADORES
# =========================================================
def _validar_df_estructuras(df: pd.DataFrame):

    if df is None:
        raise ValueError("df_estructuras es None")

    if not isinstance(df, pd.DataFrame):
        raise TypeError("df_estructuras debe ser DataFrame")

    if df.empty:
        raise ValueError("df_estructuras está vacío")

    if "Estructura" not in df.columns:
        raise ValueError(
            f"df_estructuras debe contener columna 'Estructura'. "
            f"Columnas actuales: {list(df.columns)}"
        )


def _validar_hojas_base(hojas_base):

    if hojas_base is None:
        raise ValueError("hojas_base es None")

    if not isinstance(hojas_base, dict):
        raise TypeError("hojas_base debe ser dict[str, DataFrame]")

    if not hojas_base:
        raise ValueError("hojas_base está vacío")


def _validar_df_salida(df: pd.DataFrame):

    if df is None or df.empty:
        raise ValueError("Resultado de materiales vacío")

    if not set(COLUMNAS_STD).issubset(df.columns):
        raise ValueError(
            f"Columnas inválidas. Esperadas: {COLUMNAS_STD}, "
            f"recibidas: {list(df.columns)}"
        )

    if df["Materiales"].isna().any():
        raise ValueError("Materiales contiene nulos")

    if df["Unidad"].isna().any():
        raise ValueError("Unidad contiene nulos")

    cantidades = pd.to_numeric(df["Cantidad"], errors="coerce")

    if cantidades.isna().any():
        raise ValueError("Cantidad inválida")

    if (cantidades < 0).any():
        raise ValueError("Cantidad negativa")


# =========================================================
# CONSOLIDACIÓN GLOBAL
# =========================================================
def _consolidar(df: pd.DataFrame) -> pd.DataFrame:

    return (
        df
        .groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"]
        .sum()
    )


# =========================================================
# FUNCIÓN PRINCIPAL (SOLO GLOBAL)
# =========================================================
def calcular_materiales_proyecto(
    hojas_base,
    df_estructuras,
    tension,
    calibre_mt=None,
    tabla_conectores_mt=None,
) -> dict:

    # -----------------------------
    # DEBUG
    # -----------------------------
    debug_guardar("CALCULO::input", {
        "filas_estructuras": None if df_estructuras is None else len(df_estructuras),
        "tension": tension,
    })

    # -----------------------------
    # VALIDACIONES
    # -----------------------------
    _validar_df_estructuras(df_estructuras)
    _validar_hojas_base(hojas_base)

    if tension is None or float(tension) <= 0:
        raise ValueError("tension no válida")

    # -----------------------------
    # CÁLCULO DETALLE
    # -----------------------------
    df_detalle = calcular_materiales_por_punto(
        hojas_base=hojas_base,
        df_estructuras=df_estructuras,
        tension=tension,
        calibre_mt=calibre_mt,
        tabla_conectores_mt=tabla_conectores_mt
    )

    _validar_df_salida(df_detalle)

    # -----------------------------
    # CONSOLIDADO GLOBAL
    # -----------------------------
    df_global = _consolidar(df_detalle)

    _validar_df_salida(df_global)

    # -----------------------------
    # SALIDA FINAL
    # -----------------------------
    return {
        "ok": True,
        "df_materiales": df_global
        "df_materiales_por_punto": df_detalle
    }
