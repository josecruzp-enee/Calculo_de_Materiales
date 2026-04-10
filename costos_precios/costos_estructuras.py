# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from typing import Dict, Any

from costos_precios.costos_materiales import calcular_lista_materiales_con_costos
from ayuda.debug import debug_guardar


# =========================================================
# COSTO UNITARIO DE UNA ESTRUCTURA
# =========================================================
def _costo_unitario_estructura(
    df_materiales: pd.DataFrame,
    df_precios: pd.DataFrame
) -> float:

    df_val = calcular_lista_materiales_con_costos(
        df_materiales=df_materiales,
        df_catalogo_costos=df_precios
    )

    if df_val is None:
        raise ValueError("df_val es None")

    if df_val.empty:
        raise ValueError("df_val vacío → sin costos")

    if "Costo Total" not in df_val.columns:
        raise ValueError(f"Columnas inválidas: {list(df_val.columns)}")

    total = df_val["Costo Total"].sum()

    if pd.isna(total) or total <= 0:
        raise ValueError("Costo total inválido")

    return float(total)


# =========================================================
# COSTOS POR ESTRUCTURA
# =========================================================
def calcular_costos_por_estructura(
    *,
    df_estructuras: pd.DataFrame,
    df_materiales_por_estructura: Dict[str, pd.DataFrame],
    df_precios_materiales: pd.DataFrame,
) -> pd.DataFrame:

    debug: Dict[str, Any] = {}

    # =====================================================
    # VALIDACIONES
    # =====================================================
    if df_estructuras is None or df_estructuras.empty:
        raise ValueError("df_estructuras vacío")

    if df_precios_materiales is None or df_precios_materiales.empty:
        raise ValueError("df_precios_materiales vacío")

    if not isinstance(df_materiales_por_estructura, dict):
        raise TypeError("df_materiales_por_estructura debe ser dict")

    # =====================================================
    # DATAFRAME BASE
    # =====================================================
    df = df_estructuras.copy()

    if "Estructura" not in df.columns or "Cantidad" not in df.columns:
        raise ValueError("df_estructuras debe tener columnas 'Estructura' y 'Cantidad'")

    # ⚠️ NO normalizar aquí
    df["codigodeestructura"] = df["Estructura"].astype(str).str.strip()
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)

    # =====================================================
    # AGRUPAR
    # =====================================================
    df_group = df.groupby("codigodeestructura", as_index=False)["Cantidad"].sum()

    debug["estructuras_detectadas"] = len(df_group)
    debug["estructuras_sample"] = df_group.head(10).to_dict()

    filas = []
    errores = []

    # =====================================================
    # LOOP PRINCIPAL
    # =====================================================
    for _, row in df_group.iterrows():

        cod = str(row["codigodeestructura"]).strip()
        qty = float(row["Cantidad"])

        if qty <= 0:
            continue

        df_mat = df_materiales_por_estructura.get(cod)

        # DEBUG CLAVE
        if df_mat is None:
            errores.append(f"{cod}: NO EXISTE EN dict")
            continue

        if df_mat.empty:
            errores.append(f"{cod}: SIN MATERIALES")
            continue

        try:
            costo_unit = _costo_unitario_estructura(df_mat, df_precios_materiales)

            filas.append({
                "codigodeestructura": cod,
                "Costo Unitario": round(costo_unit, 2),
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
            "materiales_keys": list(df_materiales_por_estructura.keys())[:20],
            "estructuras": df_group.head(20).to_dict(),
        })
        raise ValueError("No se generaron costos por estructura")

    debug["resultado"] = {
        "filas": len(df_out),
        "total_costos": float(df_out["Costo Total"].sum())
    }

    debug["errores"] = errores

    debug_guardar("COSTOS_POR_ESTRUCTURA", debug)

    return df_out
