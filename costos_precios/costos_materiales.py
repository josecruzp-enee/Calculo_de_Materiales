# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import unicodedata
from ayuda.debug import debug_guardar


# =========================================================
# NORMALIZACIÓN
# =========================================================
def _norm_txt(s: object) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""

    t = str(s).upper()

    t = "".join(
        c for c in unicodedata.normalize("NFD", t)
        if unicodedata.category(c) != "Mn"
    )

    for p in ["DE", "DEL", "LA", "EL", "ANSI", "TIPO", "CLASE",
              "CARRETE", "ESPIGA", "SUSPENSION"]:
        t = t.replace(p, "")

    t = t.replace("-", " ")
    t = "".join(c if c.isalnum() else " " for c in t)
    t = " ".join(t.split())

    return t


# =========================================================
# PREPARAR CATÁLOGO
# =========================================================
def preparar_catalogo_costos(df_catalogo: pd.DataFrame) -> pd.DataFrame:

    if df_catalogo is None or df_catalogo.empty:
        raise ValueError("Catálogo de costos vacío")

    df = df_catalogo.copy()

    df["Materiales_norm"] = df["Materiales"].astype(str).map(_norm_txt)
    df["Unidad_norm"] = df["Unidad"].astype(str).map(_norm_txt)

    df["Costo Unitario"] = pd.to_numeric(
        df.get("Costo Unitario", df.get("Costo", 0)),
        errors="coerce"
    )

    df = df.dropna(subset=["Costo Unitario"])
    df = df[df["Costo Unitario"] > 0]

    df = df.drop_duplicates(
        subset=["Materiales_norm", "Unidad_norm"]
    )

    debug_guardar("catalogo_costos_procesado", {
        "filas": len(df)
    })

    return df[["Materiales_norm", "Unidad_norm", "Costo Unitario"]]


# =========================================================
# MOTOR PRINCIPAL
# =========================================================
def calcular_lista_materiales_con_costos(
    df_materiales: pd.DataFrame,
    df_catalogo_costos: pd.DataFrame
) -> pd.DataFrame:

    if df_materiales is None or df_materiales.empty:
        raise ValueError("df_materiales vacío")

    if df_catalogo_costos is None or df_catalogo_costos.empty:
        raise ValueError("df_catalogo_costos vacío")

    df = df_materiales.copy()

    # VALIDACIÓN
    cols = {"Materiales", "Unidad", "Cantidad"}
    if not cols.issubset(df.columns):
        raise ValueError(f"df_materiales debe tener columnas {cols}")

    # CONSOLIDAR LISTA GLOBAL
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)

    df = (
        df.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"]
        .sum()
    )

    # NORMALIZAR
    df["Materiales_norm"] = df["Materiales"].map(_norm_txt)
    df["Unidad_norm"] = df["Unidad"].map(_norm_txt)

    # MERGE COSTOS
    df = df.merge(
        df_catalogo_costos,
        on=["Materiales_norm", "Unidad_norm"],
        how="left"
    )

    # DEBUG FALLAS
    faltantes = df[df["Costo Unitario"].isna()]

    debug_guardar("materiales_sin_precio", {
        "total": len(faltantes),
        "ejemplo": faltantes.head(10).to_dict()
    })

    if not faltantes.empty:
        raise ValueError("Hay materiales sin precio")

    # COSTOS
    df["Costo Total"] = df["Cantidad"] * df["Costo Unitario"]

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
