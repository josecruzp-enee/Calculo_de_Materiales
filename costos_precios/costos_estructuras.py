# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from typing import Dict, Any

from ayuda.debug import debug_guardar
from costos_precios.costos_materiales import calcular_costos_desde_resumen


# =========================================================
# COSTO UNITARIO
# =========================================================
def _costo_unitario_estructura(df_materiales, df_precios) -> float:

    df_val = calcular_costos_desde_resumen(
        df_materiales[["Materiales", "Unidad", "Cantidad"]],
        df_precios
    )

    if df_val is None or df_val.empty:
        raise ValueError("df_val vacío en costo unitario")

    if "Costo Total" not in df_val.columns:
        raise ValueError(f"Columnas inválidas: {list(df_val.columns)}")

    return float(df_val["Costo Total"].sum())


# =========================================================
# COSTOS POR ESTRUCTURA
# =========================================================
def calcular_costos_por_estructura(
    *,
    df_estructuras: pd.DataFrame,
    df_materiales_por_estructura: Dict[str, pd.DataFrame],
    df_precios_materiales: pd.DataFrame,
) -> pd.DataFrame:

    debug = {}

    if df_estructuras is None or df_estructuras.empty:
        raise ValueError("df_estructuras vacío")

    df = df_estructuras.copy()

    # =====================================================
    # NORMALIZAR
    # =====================================================
    df["codigodeestructura"] = df["Estructura"].astype(str).str.strip().str.upper()
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)

    df_group = df.groupby("codigodeestructura", as_index=False)["Cantidad"].sum()

    debug["estructuras_detectadas"] = len(df_group)

    filas = []
    errores = []

    # =====================================================
    # LOOP PRINCIPAL
    # =====================================================
    for _, row in df_group.iterrows():

        cod = row["codigodeestructura"]
        qty = float(row["Cantidad"])

        debug[f"estructura::{cod}"] = {
            "cantidad": qty
        }

        if qty <= 0:
            continue

        df_mat = df_materiales_por_estructura.get(cod)

        if df_mat is None or df_mat.empty:
            errores.append(f"Sin materiales para {cod}")
            continue   # 🔥 NO rompe el sistema

        try:
            costo_unit = _costo_unitario_estructura(df_mat, df_precios_materiales)

            filas.append({
                "codigodeestructura": cod,
                "Costo Unitario": costo_unit,
                "Cantidad": qty,
                "Costo Total": round(costo_unit * qty, 2),
            })

        except Exception as e:
            errores.append(f"{cod}: {str(e)}")

    # =========================================================
    # OUTPUT
    # =========================================================
    df_out = pd.DataFrame(filas)

    if df_out.empty:
        debug_guardar("COSTOS_ESTRUCTURA_ERROR", {
            "errores": errores,
            "warning": "No se generaron costos"
        })
        raise ValueError("No se generaron costos por estructura")

    debug["resultado"] = {
        "filas": len(df_out),
        "total_costos": float(df_out["Costo Total"].sum())
    }

    debug["errores"] = errores

    debug_guardar("COSTOS_POR_ESTRUCTURA", debug)

    return df_out
