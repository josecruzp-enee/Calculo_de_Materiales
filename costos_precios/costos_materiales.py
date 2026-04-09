# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import unicodedata
from typing import Dict, Any
from pathlib import Path

from entradas.base_datos import obtener_catalogo_materiales
from ayuda.debug import debug_guardar


# =========================================================
# NORMALIZACIÓN TEXTO
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
# MOTOR DE COSTOS (OK)
# =========================================================
# =========================================================
# MOTOR DE COSTOS (OK)
# =========================================================
def calcular_costos_desde_resumen(df_resumen, df_costos):

    if df_resumen is None or df_resumen.empty:
        raise ValueError("df_resumen vacío")

    if df_costos is None or df_costos.empty:
        raise ValueError("df_costos vacío")

    df = df_resumen.copy()

    if "Unidad" not in df.columns:
        df["Unidad"] = ""

    df["Materiales_norm"] = df["Materiales"].astype(str).map(_norm_txt)
    df["Unidad_norm"] = df["Unidad"].astype(str).map(_norm_txt)

    # 🔍 DEBUG ANTES DEL MERGE
    debug_guardar("DEBUG_PRECIOS_INPUT", {
        "df_resumen_head": df.head(5).to_dict(),
        "df_costos_head": df_costos.head(5).to_dict(),
        "resumen_filas": len(df),
        "costos_filas": len(df_costos)
    })

    df = df.merge(df_costos, on=["Materiales_norm", "Unidad_norm"], how="left")

    # 🔍 DEBUG DESPUÉS DEL MERGE (CRÍTICO)
    debug_guardar("DEBUG_PRECIOS_MERGE", {
        "columnas": list(df.columns),
        "head": df.head(10).to_dict()
    })

    # 🔍 VER FALTANTES
    faltantes = df[df["Costo Unitario"].isna()]
    debug_guardar("DEBUG_PRECIOS_FALTANTES", {
        "cantidad_faltantes": len(faltantes),
        "muestra": faltantes.head(10).to_dict()
    })

    if not faltantes.empty:
        raise ValueError("Hay materiales sin costo")

    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)
    df["Costo Total"] = df["Cantidad"] * df["Costo Unitario"]

    # 🔥 DEBUG FINAL (TABLA REAL DE COSTOS)
    debug_guardar("DEBUG_COSTOS_MATERIALES_FINAL", {
        "columnas": list(df.columns),
        "preview": df[[
            "Materiales",
            "Unidad",
            "Cantidad",
            "Costo Unitario",
            "Costo Total"
        ]].head(20).to_dict(),
        "total_costos": float(df["Costo Total"].sum())
    })

    return df[[
        "Materiales", "Unidad", "Cantidad",
        "Costo Unitario", "Costo Total"
    ]].reset_index(drop=True)

# =========================================================
# BUILDER CORRECTO (ALINEADO)
# =========================================================
def construir_entrada_costos(
    data: Dict[str, Any],
    df_resumen: pd.DataFrame,
    df_estructuras_por_punto: pd.DataFrame,
    df_materiales_por_punto: pd.DataFrame
):

    if df_materiales_por_punto is None:
        raise ValueError("df_materiales_por_punto es requerido")

    catalogo = obtener_catalogo_materiales(data)

    df_costos = preparar_df_costos_unitarios(catalogo)

    # DEBUG
    debug_guardar("builder_costos", {
        "catalogo_filas": len(catalogo),
        "costos_filas": len(df_costos),
        "materiales_por_punto_filas": len(df_materiales_por_punto),
    })

    from costos_precios.orquestador_costos import EntradaCostos

    return EntradaCostos(
        df_resumen=df_resumen,
        df_estructuras_por_punto=df_estructuras_por_punto,
        df_materiales_por_punto=df_materiales_por_punto,
        fuente_precios=df_costos,
    )


# =========================================================
# COSTOS UNITARIOS
# =========================================================
def preparar_df_costos_unitarios(df_catalogo):

    if df_catalogo is None or df_catalogo.empty:
        raise ValueError("Catálogo vacío")

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

    # DEBUG
    debug_guardar("catalogo_procesado", {
        "filas_finales": len(df)
    })

    return df[["Materiales_norm", "Unidad_norm", "Costo Unitario"]]
