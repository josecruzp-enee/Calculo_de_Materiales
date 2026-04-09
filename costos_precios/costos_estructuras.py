# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from typing import Dict

from costos_precios.costos_materiales import calcular_costos_desde_resumen


# =====================================================
# 🔹 COSTO UNITARIO DE UNA ESTRUCTURA (SOLO MATERIALES)
# =====================================================
def _costo_unitario_estructura(
    df_materiales: pd.DataFrame,
    df_precios_materiales: pd.DataFrame,
) -> float:

    df_val = calcular_costos_desde_resumen(
        df_materiales[["Materiales", "Unidad", "Cantidad"]],
        df_precios_materiales
    )

    if not isinstance(df_val, pd.DataFrame) or df_val.empty:
        raise ValueError("Valorización vacía")

    if "Costo Total" not in df_val.columns:
        raise ValueError(f"Columnas inválidas: {list(df_val.columns)}")

    costo = float(
        pd.to_numeric(df_val["Costo Total"], errors="coerce")
        .fillna(0)
        .sum()
    )

    if costo <= 0:
        raise ValueError("Costo de estructura inválido")

    return round(costo, 2)


# =====================================================
# 🔹 FUNCIÓN PRINCIPAL
# =====================================================
def calcular_costos_por_estructura(
    *,
    df_estructuras: pd.DataFrame,
    df_materiales_por_estructura: Dict[str, pd.DataFrame],
    df_precios_materiales: pd.DataFrame,
) -> pd.DataFrame:

    if df_estructuras is None or df_estructuras.empty:
        raise ValueError("df_estructuras vacío")

    # -------------------------------
    # NORMALIZACIÓN
    # -------------------------------
    df = df_estructuras.copy()

    df["codigodeestructura"] = df["Estructura"].astype(str).str.strip().str.upper()
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)

    # 🔥 AGRUPAR (1 fila por estructura)
    df_group = df.groupby("codigodeestructura", as_index=False)["Cantidad"].sum()

    filas = []

    # -------------------------------
    # LOOP
    # -------------------------------
    for _, row in df_group.iterrows():

        cod = row["codigodeestructura"]
        qty = int(row["Cantidad"])

        if qty <= 0:
            continue

        df_mat = df_materiales_por_estructura.get(cod)

        if df_mat is None or df_mat.empty:
            raise ValueError(f"Sin materiales para: {cod}")

        costo_unit = _costo_unitario_estructura(
            df_materiales=df_mat,
            df_precios_materiales=df_precios_materiales,
        )

        filas.append({
            "codigodeestructura": cod,              # 🔥 OBLIGATORIO
            "Costo Unitario": costo_unit,           # 🔥 OBLIGATORIO
            "Precio Unitario": costo_unit,          # 🔥 OBLIGATORIO
            "Cantidad": qty,
            "Costo Total": round(costo_unit * qty, 2),
        })

    df_out = pd.DataFrame(filas)

    if df_out.empty:
        raise ValueError("No se generaron costos")

    # 🔥 GARANTÍA FINAL DEL CONTRATO (CRÍTICO)
    required = {"codigodeestructura", "Costo Unitario", "Precio Unitario"}
    if not required.issubset(df_out.columns):
        raise ValueError(f"Salida inválida: {df_out.columns}")

    return df_out.sort_values("codigodeestructura").reset_index(drop=True)
