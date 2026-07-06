# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import re
from ayuda.debug import debug_guardar


# =========================================================
# 🔧 NORMALIZADOR CENTRAL (CLAVE DEL SISTEMA)
# =========================================================
def _norm_text(s: str) -> str:
    return (
        str(s)
        .upper()
        .replace('"', '')
        .replace('\n', ' ')
        .strip()
    )


def _norm_material(s: str) -> str:
    return (
        _norm_text(s)
        .replace("  ", " ")
    )


# =========================================================
# 🔧 NORMALIZAR DATAFRAME (REUTILIZABLE)
# =========================================================
def _normalizar_materiales_df(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()

    df["Materiales"] = df["Materiales"].apply(_norm_material)
    df["Unidad"] = df["Unidad"].apply(_norm_text)

    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0.0)

    return df


def _normalizar_catalogo_df(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()

    df["Materiales"] = df["Materiales"].apply(_norm_material)
    df["Unidad"] = df["Unidad"].apply(_norm_text)

    df["Costo Unitario"] = pd.to_numeric(
        df["Costo Unitario"],
        errors="coerce"
    )

    return df


# =========================================================
# PREPARAR CATÁLOGO
# =========================================================
def preparar_catalogo_costos(df_catalogo: pd.DataFrame) -> pd.DataFrame:

    if df_catalogo is None or df_catalogo.empty:
        raise ValueError("Catálogo de costos vacío")

    df = df_catalogo.copy()
    df.columns = [str(c).strip() for c in df.columns]

    col_material = None
    col_unidad = None
    col_costo = None

    for c in df.columns:
        c_up = c.upper()

        if "MATER" in c_up:
            col_material = c
        elif "UNIDAD" in c_up:
            col_unidad = c
        elif "COSTO" in c_up:
            col_costo = c

    if not all([col_material, col_unidad, col_costo]):
        raise ValueError(f"No se pudieron detectar columnas válidas: {df.columns}")

    df = df[[col_material, col_unidad, col_costo]].copy()
    df.columns = ["Materiales", "Unidad", "Costo Unitario"]

    df = _normalizar_catalogo_df(df)

    df = df.dropna(subset=["Costo Unitario"])
    df = df[df["Costo Unitario"] > 0]

    df = df.drop_duplicates(subset=["Materiales", "Unidad"])

    debug_guardar("catalogo_costos_procesado", {
        "filas": len(df),
        "preview": df.head(10).to_dict(orient="records")
    })

    return df


# =========================================================
# 🔧 CONSOLIDAR MATERIALES
# =========================================================
def _consolidar_materiales(df: pd.DataFrame) -> pd.DataFrame:

    return (
        df
        .groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"]
        .sum()
    )


# =========================================================
# 🔧 MERGE CON COSTOS
# =========================================================
def _merge_costos(df: pd.DataFrame, catalogo: pd.DataFrame) -> pd.DataFrame:

    df = df.merge(
        catalogo,
        on=["Materiales", "Unidad"],
        how="left"
    )

    return df


# =========================================================
# 🔧 FILTRAR SIN COSTO
# =========================================================
def _filtrar_sin_costo(df: pd.DataFrame) -> pd.DataFrame:

    faltantes = df[df["Costo Unitario"].isna()]

    if not faltantes.empty:
        debug_guardar("WARNING_MATERIALES_SIN_COSTO", {
            "cantidad": len(faltantes),
            "ejemplo": faltantes.head(10).to_dict(orient="records")
        })

        df = df.dropna(subset=["Costo Unitario"])

    if df.empty:
        raise ValueError("Todos los materiales quedaron sin costo")

    return df


# =========================================================
# 🔧 CALCULAR COSTOS
# =========================================================
def _calcular_costos(df: pd.DataFrame) -> pd.DataFrame:

    df["Costo Total"] = df["Cantidad"] * df["Costo Unitario"]

    return df


# =========================================================
# 🔥 FUNCIÓN PRINCIPAL (LIMPIA)
# =========================================================
def calcular_lista_materiales_con_costos(
    df_materiales: pd.DataFrame,
    df_catalogo_costos: pd.DataFrame
) -> pd.DataFrame:

    if df_materiales is None or df_materiales.empty:
        raise ValueError("df_materiales vacío")

    if df_catalogo_costos is None or df_catalogo_costos.empty:
        raise ValueError("df_catalogo_costos vacío")

    df = _normalizar_materiales_df(df_materiales)
    catalogo = preparar_catalogo_costos(df_catalogo_costos)

    df = _consolidar_materiales(df)

    debug_guardar("DEBUG_MATCH_KEYS", {
        "proyecto": df["Materiales"].unique().tolist()[:10],
        "catalogo": catalogo["Materiales"].unique().tolist()[:10]
    })

    df = _merge_costos(df, catalogo)
    df = _filtrar_sin_costo(df)
    df = _calcular_costos(df)

    debug_guardar("resultado_costos_materiales", {
        "total_materiales": len(df),
        "costo_total": float(df["Costo Total"].sum())
    })

    return df[[
        "Materiales",
        "Unidad",
        "Cantidad",
        "Costo Unitario",
        "Costo Total"
    ]].reset_index(drop=True)
