# -*- coding: utf-8 -*-

from __future__ import annotations
import pandas as pd

from materiales.calculos.materiales_puntos import (
    calcular_materiales_por_punto,
    extraer_conteo_estructuras,
)

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
        raise ValueError("df_estructuras debe contener columna 'Estructura'")

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
        raise ValueError("Columnas inválidas en salida")

    if df["Materiales"].isna().any():
        raise ValueError("Materiales contiene valores nulos")

    if df["Unidad"].isna().any():
        raise ValueError("Unidad contiene valores nulos")

    cantidades = pd.to_numeric(df["Cantidad"], errors="coerce")

    if cantidades.isna().any():
        raise ValueError("Cantidad contiene valores inválidos")

    if (cantidades < 0).any():
        raise ValueError("Cantidad contiene valores negativos")


def _consolidar(df: pd.DataFrame) -> pd.DataFrame:

    if df is None or df.empty:
        return pd.DataFrame(columns=COLUMNAS_STD)

    return (
        df
        .groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"]
        .sum()
    )


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================
def calcular_materiales_proyecto(
    hojas_base,
    df_estructuras,
    tension,
    calibre_mt=None,
    tabla_conectores_mt=None,
) -> dict:

    # =========================
    # VALIDACIONES INICIALES
    # =========================
    _validar_df_estructuras(df_estructuras)
    _validar_hojas_base(hojas_base)

    if tension is None or float(tension) <= 0:
        raise ValueError("tension no válida")

    # =========================
    # CÁLCULO REAL (FUENTE ÚNICA)
    # =========================
    df_detalle = calcular_materiales_por_punto(
        hojas_base=hojas_base,
        df_estructuras=df_estructuras,
        tension=tension,
        calibre_mt=calibre_mt,
        tabla_conectores_mt=tabla_conectores_mt
    )

    # =========================
    # VALIDACIÓN DETALLE
    # =========================
    _validar_df_salida(df_detalle)

    # =========================
    # CONSOLIDACIÓN
    # =========================
    df_resumen = _consolidar(df_detalle)

    # =========================
    # VALIDACIÓN FINAL
    # =========================
    _validar_df_salida(df_resumen)

    # =========================
    # CONTEO (solo informativo)
    # =========================
    conteo, estructuras_por_punto = extraer_conteo_estructuras(df_estructuras)

    # =========================
    # SALIDA
    # =========================
    return {
        "ok": True,
        "df_materiales": df_resumen,
        "df_materiales_detalle": df_detalle,
        "conteo_estructuras": conteo,
        "estructuras_por_punto": estructuras_por_punto,
    }
