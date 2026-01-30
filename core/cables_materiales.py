# -*- coding: utf-8 -*-
"""
core/cables_materiales.py

Convierte la tabla de cables del proyecto (UI) a materiales compatibles con el catálogo:
Salida: DataFrame con columnas EXACTAS: ["Materiales", "Unidad", "Cantidad"]

Regla (Opción A):
- "Materiales" = nombre real del material (tomado desde df_cables["Calibre"])
- "Unidad"     = "Pie"
- "Cantidad"   = Total Cable (m) convertido a pies
"""

from __future__ import annotations

from typing import Optional
import pandas as pd


_M_A_PIE = 3.28084


def _a_float(v) -> float:
    try:
        x = float(v)
        return x if x >= 0 else 0.0
    except Exception:
        return 0.0


def materiales_desde_cables(df_cables: Optional[pd.DataFrame]) -> pd.DataFrame:
    """
    Espera df_cables con columnas típicas:
    - "Calibre" (texto del material real)
    - "Total Cable (m)" (numérico)  (preferida)
      o "Longitud" (m) si no existe Total Cable (m)

    Retorna:
      DataFrame: ["Materiales", "Unidad", "Cantidad"] con Unidad="Pie"
    """
    if df_cables is None or not isinstance(df_cables, pd.DataFrame) or df_cables.empty:
        return pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])

    df = df_cables.copy()

    # Determinar columna de longitud total en metros
    col_total_m = None
    for c in ["Total Cable (m)", "Total", "Total_m", "Longitud", "Longitud (m)"]:
        if c in df.columns:
            col_total_m = c
            break

    if col_total_m is None:
        # No hay nada que calcular
        return pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])

    # Nombre real del material (del catálogo)
    if "Calibre" not in df.columns:
        # fallback mínimo (para no reventar)
        df["Calibre"] = ""

    filas = []
    for _, r in df.iterrows():
        material = str(r.get("Calibre", "")).strip()
        if not material:
            continue

        total_m = _a_float(r.get(col_total_m, 0.0))
        total_pie = total_m * _M_A_PIE

        filas.append({
            "Materiales": material,
            "Unidad": "Pie",
            "Cantidad": round(total_pie, 2),
        })

    if not filas:
        return pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])

    out = pd.DataFrame(filas)
    # Consolidar por si hay calibres repetidos
    out = out.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
    return out
