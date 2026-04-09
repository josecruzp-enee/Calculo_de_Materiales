# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from typing import Dict

from costos_precios.costos_materiales import calcular_costos_desde_resumen


def _costo_unitario_estructura(df_materiales, df_precios):
    df_val = calcular_costos_desde_resumen(
        df_materiales[["Materiales", "Unidad", "Cantidad"]],
        df_precios
    )

    if "Costo Total" not in df_val.columns:
        raise ValueError(f"Columnas inválidas: {df_val.columns}")

    return float(df_val["Costo Total"].sum())


def calcular_costos_por_estructura(
    *,
    df_estructuras: pd.DataFrame,
    df_materiales_por_estructura: Dict[str, pd.DataFrame],
    df_precios_materiales: pd.DataFrame,
) -> pd.DataFrame:

    df = df_estructuras.copy()

    df["codigodeestructura"] = df["Estructura"].astype(str).str.strip().str.upper()
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)

    df_group = df.groupby("codigodeestructura", as_index=False)["Cantidad"].sum()

    filas = []

    for _, row in df_group.iterrows():

        cod = row["codigodeestructura"]
        qty = int(row["Cantidad"])

        if qty <= 0:
            continue

        df_mat = df_materiales_por_estructura.get(cod)

        if df_mat is None or df_mat.empty:
            raise ValueError(f"Sin materiales para: {cod}")

        costo_unit = _costo_unitario_estructura(df_mat, df_precios_materiales)

        filas.append({
            "codigodeestructura": cod,
            "Costo Unitario": costo_unit,
            "Precio Unitario": costo_unit,
            "Cantidad": qty,
            "Costo Total": round(costo_unit * qty, 2),
        })

    df_out = pd.DataFrame(filas)

    if df_out.empty:
        raise ValueError("No se generaron costos")

    return df_out
