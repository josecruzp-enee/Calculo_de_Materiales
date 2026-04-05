# -*- coding: utf-8 -*-

from __future__ import annotations
import pandas as pd

from materiales.calculos.materiales_puntos import (
    calcular_materiales_por_punto,
    extraer_conteo_estructuras,
)


COLUMNAS_STD = ["Materiales", "Unidad", "Cantidad"]


# =========================================================
# VALIDADORES INTERNOS
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

    # =====================================================
    # VALIDACIONES
    # =====================================================
    _validar_df_estructuras(df_estructuras)
    _validar_hojas_base(hojas_base)

    if tension is None:
        raise ValueError("tension no definida")

    # =====================================================
    # CONTEO DE ESTRUCTURAS
    # =====================================================
    conteo, estructuras_por_punto = extraer_conteo_estructuras(df_estructuras)

    # =====================================================
    # CÁLCULO PRINCIPAL
    # =====================================================
    df_materiales = calcular_materiales_por_punto(
        hojas_base=hojas_base,
        df_estructuras=df_estructuras,
        tension=tension,
        calibre_mt=calibre_mt,
        tabla_conectores_mt=tabla_conectores_mt
    )

    # =====================================================
    # NORMALIZACIÓN
    # =====================================================
    if df_materiales is None or df_materiales.empty:

        df_materiales = pd.DataFrame(columns=COLUMNAS_STD)

        df_resumen = df_materiales.copy()

    else:

        # limpieza básica
        df_materiales = df_materiales.copy()

        df_materiales["Materiales"] = df_materiales["Materiales"].astype(str).str.strip()
        df_materiales["Unidad"] = df_materiales["Unidad"].astype(str).str.strip()
        df_materiales["Cantidad"] = pd.to_numeric(
            df_materiales["Cantidad"], errors="coerce"
        ).fillna(0)

        # consolidación
        df_resumen = (
            df_materiales
            .groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"]
            .sum()
        )

    # =====================================================
    # VALIDACIÓN FINAL
    # =====================================================
    if not set(COLUMNAS_STD).issubset(df_resumen.columns):
        raise ValueError("Salida inválida en materiales")

    # =====================================================
    # SALIDA
    # =====================================================
    return {
        "ok": True,
        "df_materiales": df_resumen,
        "df_materiales_detalle": df_materiales,
        "conteo_estructuras": conteo,
        "estructuras_por_punto": estructuras_por_punto,
    }
