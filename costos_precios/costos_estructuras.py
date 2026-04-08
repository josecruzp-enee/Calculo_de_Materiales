# -*- coding: utf-8 -*-

from __future__ import annotations

import pandas as pd
from typing import Dict, Optional

# 🔥 IMPORTS CORRECTOS (CRÍTICO)
from materiales.calculos.calculo_estructura import calcular_materiales_estructura
from costos_precios.costos_materiales import calcular_costos_desde_resumen

from costos.costos_operativos import calcular_costos_operativos
from costos.precios_venta import calcular_precio_venta


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

    # 🔥 PARÁMETROS OPERATIVOS
    costo_cuadrilla_dia: float = 1250,
    fraccion_jornada: float = 1/16,
    costo_equipos: float = 0.0,
    costo_logistica: float = 0.0,
    margen_utilidad: float = 0.15,
) -> pd.DataFrame:

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
                1,
                tension_ll,
                calibre_mt,
                tabla_conectores_mt,
            )
        except Exception as e:
            raise RuntimeError(f"Error materiales estructura {cod}: {e}")

        if df_mat is None or df_mat.empty:
            costo_material = 0.0
        else:
            df_val = calcular_costos_desde_resumen(
                df_mat[["Materiales", "Unidad", "Cantidad"]],
                archivo_materiales
            )

            costo_material = float(
                pd.to_numeric(df_val["Costo"], errors="coerce")
                .fillna(0.0)
                .sum()
            )

        # -------------------------------------------------
        # 2) COSTOS OPERATIVOS
        # -------------------------------------------------
        costos_op = calcular_costos_operativos(
            costo_cuadrilla_dia=costo_cuadrilla_dia,
            fraccion_jornada=fraccion_jornada,
            costo_equipos=costo_equipos,
            costo_logistica=costo_logistica,
        )

        costo_operativo = costos_op["operativo_total"]

        # -------------------------------------------------
        # 3) COSTO TOTAL
        # -------------------------------------------------
        costo_total = costo_material + costo_operativo

        # -------------------------------------------------
        # 4) PRECIO DE VENTA
        # -------------------------------------------------
        venta = calcular_precio_venta(
            costo_total=costo_total,
            margen_utilidad=margen_utilidad
        )

        precio_unitario = venta["precio_venta"]

        # -------------------------------------------------
        # VALIDACIÓN FUERTE (IMPORTANTE)
        # -------------------------------------------------
        if precio_unitario <= 0:
            raise ValueError(f"Estructura sin precio válido: {cod}")

        # -------------------------------------------------
        # RESULTADO
        # -------------------------------------------------
        filas.append({
            "codigodeestructura": cod,
            "Cantidad": qty,
            "Costo Material": round(costo_material, 2),
            "Costo Operativo": round(costo_operativo, 2),
            "Costo Unitario": round(costo_total, 2),
            "Precio Unitario": round(precio_unitario, 2),
            "Total": round(precio_unitario * qty, 2),
        })

    if not filas:
        raise ValueError("No se generaron costos por estructura")

    return pd.DataFrame(filas).sort_values("codigodeestructura").reset_index(drop=True)
