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

    if "Estructuras" not in df.columns:
        raise ValueError("df_estructuras debe contener columna 'Estructuras'")


def _validar_hojas_base(hojas_base):
    if hojas_base is None:
        raise ValueError("hojas_base es None")

    if not isinstance(hojas_base, dict):
        raise TypeError("hojas_base debe ser dict[str, DataFrame]")

    if not hojas_base:
        raise ValueError("hojas_base está vacío")


def _normalizar_df(df: pd.DataFrame) -> pd.DataFrame:

    if df is None or df.empty:
        return pd.DataFrame(columns=COLUMNAS_STD)

    df = df.copy()

    df["Materiales"] = df["Materiales"].astype(str).str.strip()
    df["Unidad"] = df["Unidad"].astype(str).str.strip()
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)

    return df[COLUMNAS_STD]


def _consolidar(df: pd.DataFrame) -> pd.DataFrame:

    if df.empty:
        return df

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
    # VALIDACIONES
    # =========================
    _validar_df_estructuras(df_estructuras)
    _validar_hojas_base(hojas_base)

    if tension is None or tension == 0:
        raise ValueError("tension no válida")

    # =========================
    # CONTEO (solo para salida)
    # =========================
    conteo, estructuras_por_punto = extraer_conteo_estructuras(df_estructuras)

    # =========================
    # CÁLCULO REAL (ÚNICO)
    # =========================
    df_detalle = calcular_materiales_por_punto(
        hojas_base=hojas_base,
        df_estructuras=df_estructuras,
        tension=tension,
        calibre_mt=calibre_mt,
        tabla_conectores_mt=tabla_conectores_mt
    )

    # =========================
    # NORMALIZACIÓN
    # =========================
    df_detalle = _normalizar_df(df_detalle)

    # =========================
    # CONSOLIDACIÓN (resumen)
    # =========================
    df_resumen = _consolidar(df_detalle)

    # =========================
    # VALIDACIÓN FINAL
    # =========================
    if not set(COLUMNAS_STD).issubset(df_resumen.columns):
        raise ValueError("Salida inválida en materiales")

    # =========================
    # SALIDA
    # =========================
    return {
        "ok": True,
        "df_materiales": df_resumen,           # 🔥 resumen
        "df_materiales_detalle": df_detalle,   # 🔥 detalle real
        "conteo_estructuras": conteo,
        "estructuras_por_punto": estructuras_por_punto,
    }
