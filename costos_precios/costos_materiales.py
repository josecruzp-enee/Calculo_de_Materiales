# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from ayuda.debug import debug_guardar


# =========================================================
# PREPARAR CATÁLOGO (SIN NORMALIZACIÓN)
# =========================================================
def preparar_catalogo_costos(df_catalogo: pd.DataFrame) -> pd.DataFrame:

    from ayuda.debug import debug_guardar

    if df_catalogo is None or df_catalogo.empty:
        raise ValueError("Catálogo de costos vacío")

    df = df_catalogo.copy()

    # =====================================================
    # NORMALIZAR NOMBRES DE COLUMNAS
    # =====================================================
    df.columns = [str(c).strip() for c in df.columns]

    # =====================================================
    # DETECCIÓN FLEXIBLE DE COLUMNAS
    # =====================================================
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

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    if not all([col_material, col_unidad, col_costo]):
        raise ValueError(f"No se pudieron detectar columnas válidas: {df.columns}")

    # =====================================================
    # FORMATO ESTÁNDAR
    # =====================================================
    df = df[[col_material, col_unidad, col_costo]].copy()
    df.columns = ["Materiales", "Unidad", "Costo Unitario"]

    # =====================================================
    # LIMPIEZA MÍNIMA (NO destructiva)
    # =====================================================
    df["Materiales"] = df["Materiales"].astype(str).str.strip()
    df["Unidad"] = df["Unidad"].astype(str).str.strip()

    df["Costo Unitario"] = pd.to_numeric(
        df["Costo Unitario"],
        errors="coerce"
    )

    # =====================================================
    # FILTRO DE DATOS VÁLIDOS
    # =====================================================
    df = df.dropna(subset=["Costo Unitario"])
    df = df[df["Costo Unitario"] > 0]

    # =====================================================
    # ELIMINAR DUPLICADOS
    # =====================================================
    df = df.drop_duplicates(subset=["Materiales", "Unidad"])

    # =====================================================
    # DEBUG
    # =====================================================
    debug_guardar("catalogo_costos_procesado", {
        "filas": len(df),
        "columnas": list(df.columns),
        "preview": df.head(10).to_dict(orient="records")
    })

    return df[["Materiales", "Unidad", "Costo Unitario"]]
# =========================================================
# MOTOR PRINCIPAL
# =========================================================
def calcular_lista_materiales_con_costos(
    df_materiales: pd.DataFrame,
    df_catalogo_costos: pd.DataFrame
) -> pd.DataFrame:

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    if df_materiales is None or df_materiales.empty:
        raise ValueError("df_materiales vacío")

    if df_catalogo_costos is None or df_catalogo_costos.empty:
        raise ValueError("df_catalogo_costos vacío")

    df = df_materiales.copy()

    required = {"Materiales", "Unidad", "Cantidad"}
    if not required.issubset(df.columns):
        raise ValueError(f"df_materiales debe tener columnas {required}")

    # =====================================================
    # CONSOLIDAR
    # =====================================================
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)

    df = (
        df.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"]
        .sum()
    )

    # =====================================================
    # LIMPIEZA SUAVE (NO destructiva)
    # =====================================================
    df["Materiales"] = df["Materiales"].astype(str).str.strip()
    df["Unidad"] = df["Unidad"].astype(str).str.strip()

    df_catalogo_costos = df_catalogo_costos.copy()
    df_catalogo_costos["Materiales"] = df_catalogo_costos["Materiales"].astype(str).str.strip()
    df_catalogo_costos["Unidad"] = df_catalogo_costos["Unidad"].astype(str).str.strip()

    debug_guardar("DEBUG_CATALOGO", df_catalogo_costos.head(10).to_dict(orient="records"))
    debug_guardar("DEBUG_PROYECTO", df.head(10).to_dict(orient="records"))
    # =====================================================
    # MERGE DIRECTO (SIN NORMALIZAR)
    # =====================================================
    df = df.merge(
        df_catalogo_costos,
        on=["Materiales", "Unidad"],
        how="left"
    )

    # =====================================================
    # DEBUG COMPLETO
    # =====================================================
    debug_guardar("tabla_costos_debug", {
        "filas": len(df),
        "columnas": list(df.columns),
        "preview": df.head(20).to_dict(orient="records")
    })

    # =====================================================
    # DETECTAR FALTANTES
    # =====================================================
    faltantes = df[df["Costo Unitario"].isna()]

    debug_guardar("materiales_sin_precio", {
        "total": len(faltantes),
        "ejemplo": faltantes.head(20).to_dict(orient="records")
    })

    # =====================================================
    # FILTRAR SOLO LOS QUE TIENEN COSTO
    # =====================================================
    if not faltantes.empty:
        debug_guardar("WARNING_MATERIALES_SIN_COSTO", {
            "mensaje": "Hay materiales sin precio, se excluirán",
            "cantidad": len(faltantes)
        })

        df = df.dropna(subset=["Costo Unitario"])

    # =====================================================
    # VALIDAR RESULTADO
    # =====================================================
    if df.empty:
        raise ValueError("Todos los materiales quedaron sin costo")

    # =====================================================
    # COSTOS
    # =====================================================
    df["Costo Total"] = df["Cantidad"] * df["Costo Unitario"]

    debug_guardar("resultado_costos_materiales", {
        "total_materiales": len(df),
        "costo_total": float(df["Costo Total"].sum())
    })

    # =====================================================
    # OUTPUT
    # =====================================================
    return df[[
        "Materiales",
        "Unidad",
        "Cantidad",
        "Costo Unitario",
        "Costo Total"
    ]].reset_index(drop=True)
