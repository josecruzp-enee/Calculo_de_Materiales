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


# =========================================================
# COSTOS POR ESTRUCTURA
# =========================================================
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
    Retorna DataFrame:
    codigodeestructura, Descripcion, Cantidad, Costo Unitario, Costo Total
    """

    # -----------------------------------------------------
    # VALIDACIÓN FUERTE
    # -----------------------------------------------------
    if not archivo_materiales:
        raise ValueError("archivo_materiales requerido")

    if not isinstance(conteo, dict) or not conteo:
        raise ValueError("conteo inválido o vacío")

    if tabla_conectores_mt is None or tabla_conectores_mt.empty:
        raise ValueError("tabla_conectores_mt inválida")

    # -----------------------------------------------------
    # MAPA DE DESCRIPCIONES
    # -----------------------------------------------------
    desc_map = {}

    if isinstance(df_indice, pd.DataFrame) and not df_indice.empty:

        col_code = None
        col_desc = None

        for c in df_indice.columns:
            cl = str(c).lower()

            if "estructura" in cl or "codigo" in cl:
                col_code = c

            if "descripcion" in cl or "descripción" in cl:
                col_desc = c

        if col_code and col_desc:
            desc_map = dict(
                zip(
                    df_indice[col_code].astype(str).str.strip(),
                    df_indice[col_desc].astype(str).str.strip()
                )
            )

    # -----------------------------------------------------
    # PROCESAMIENTO
    # -----------------------------------------------------
    filas = []

    for cod, qty in conteo.items():

        cod = str(cod).strip()

        try:
            qty = int(qty or 0)
        except Exception:
            qty = 0

        if not cod or qty <= 0:
            continue

        # -------------------------------------------------
        # 1) MATERIALES UNITARIOS
        # -------------------------------------------------
        try:
            df_mat = calcular_materiales_estructura(
                archivo_materiales,
                cod,
                1,  # costo unitario
                tension_ll,
                calibre_mt,
                tabla_conectores_mt,
            )
        except Exception as e:
            raise RuntimeError(f"Error calculando materiales de estructura {cod}: {e}")

        # -------------------------------------------------
        # 2) COSTEO
        # -------------------------------------------------
        if df_mat is None or df_mat.empty:
            costo_unit = 0.0
        else:
            try:
                df_val = calcular_costos_desde_resumen(
                    df_mat[["Materiales", "Unidad", "Cantidad"]],
                    archivo_materiales
                )

                costo_unit = float(
                    pd.to_numeric(df_val["Costo"], errors="coerce")
                    .fillna(0.0)
                    .sum()
                )

            except Exception as e:
                raise RuntimeError(f"Error calculando costos de estructura {cod}: {e}")

        # -------------------------------------------------
        # RESULTADO
        # -------------------------------------------------
        filas.append({
            "codigodeestructura": cod,
            "Descripcion": desc_map.get(cod, ""),
            "Cantidad": qty,
            "Costo Unitario": round(costo_unit, 2),
            "Costo Total": round(costo_unit * qty, 2),
        })

    # -----------------------------------------------------
    # OUTPUT
    # -----------------------------------------------------
    if not filas:
        return pd.DataFrame(
            columns=[
                "codigodeestructura",
                "Descripcion",
                "Cantidad",
                "Costo Unitario",
                "Costo Total"
            ]
        )

    out = pd.DataFrame(filas)

    return out.sort_values(["codigodeestructura"]).reset_index(drop=True)
