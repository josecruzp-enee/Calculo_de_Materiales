# -*- coding: utf-8 -*-
"""
core/costos_estructuras.py

Calcula costo unitario y total por estructura usando:
- materiales de la estructura (cantidad=1)
- precios por material (core/costos_materiales.py)
"""

from __future__ import annotations
from typing import Dict, Optional
import pandas as pd

from core.costos_materiales import calcular_costos_desde_resumen
from core.materiales_estructuras import calcular_materiales_estructura


def calcular_costos_por_estructura(
    *,
    archivo_materiales: str,
    conteo: Dict[str, int],
    tension_ll: float,
    calibre_mt: str,
    tabla_conectores_mt: pd.DataFrame,
    df_indice: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Retorna DF:
      codigodeestructura, Descripcion, Cantidad, Costo Unitario, Costo Total
    """
    filas = []

    # mapa de descripción si viene el índice
    desc_map = {}
    if isinstance(df_indice, pd.DataFrame) and not df_indice.empty:
        # intenta varias columnas típicas
        col_code = "codigodeestructura" if "codigodeestructura" in df_indice.columns else (
            "Estructura" if "Estructura" in df_indice.columns else None
        )
        col_desc = "Descripcion" if "Descripcion" in df_indice.columns else (
            "Descripción" if "Descripción" in df_indice.columns else None
        )
        if col_code and col_desc:
            desc_map = dict(zip(df_indice[col_code].astype(str), df_indice[col_desc].astype(str)))

    for cod, qty in conteo.items():
        qty = int(qty or 0)
        if qty <= 0:
            continue

        # 1) materiales de la estructura para 1 unidad
        df_mat = calcular_materiales_estructura(
            archivo_materiales,
            cod,
            1,  # 👈 costo unitario de estructura
            tension_ll,
            calibre_mt,
            tabla_conectores_mt,
        )

        if df_mat is None or df_mat.empty:
            costo_unit = 0.0
        else:
            # 2) valorar materiales con precios (usa tu core/costos_materiales.py)
            df_val = calcular_costos_desde_resumen(df_mat[["Materiales", "Unidad", "Cantidad"]], archivo_materiales)
            costo_unit = float(pd.to_numeric(df_val["Costo"], errors="coerce").fillna(0.0).sum())

        filas.append({
            "codigodeestructura": str(cod),
            "Descripcion": desc_map.get(str(cod), ""),
            "Cantidad": qty,
            "Costo Unitario": round(costo_unit, 2),
            "Costo Total": round(costo_unit * qty, 2),
        })

    out = pd.DataFrame(filas)
    if out.empty:
        return pd.DataFrame(columns=["codigodeestructura","Descripcion","Cantidad","Costo Unitario","Costo Total"])

    # orden opcional
    return out.sort_values(["codigodeestructura"]).reset_index(drop=True)
