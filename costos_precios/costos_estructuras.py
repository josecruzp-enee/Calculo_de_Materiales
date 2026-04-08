# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from typing import Dict, Optional

from materiales.calculos.materiales_puntos import calcular_materiales_estructura
from costos_precios.costos_materiales import calcular_costos_desde_resumen
from costos_precios.costos_operativos import calcular_costos_operativos


def calcular_costos_por_estructura(
    *,
    hojas_base: dict,
    conteo: Dict[str, int],
    tension_ll: float,
    calibre_mt: str,
    tabla_conectores_mt: pd.DataFrame,

    costo_cuadrilla_dia: float = 1250,
    fraccion_jornada: float = 1/16,
    costo_equipos: float = 0.0,
    costo_logistica: float = 0.0,
    margen_utilidad: float = 0.15,
) -> pd.DataFrame:

    filas = []

    for cod, qty in conteo.items():

        cod = str(cod).strip().upper()

        qty = int(qty or 0)
        if qty <= 0:
            continue

        # -------------------------------------------------
        # 1) MATERIALES UNITARIOS
        # -------------------------------------------------
        df_mat = calcular_materiales_estructura(
            hojas_base=hojas_base,
            estructura=cod,
            cantidad=1,
            tension=tension_ll,
            calibre_mt=calibre_mt,
            tabla_conectores_mt=tabla_conectores_mt,
        )

        df_val = calcular_costos_desde_resumen(
            df_mat[["Materiales", "Unidad", "Cantidad"]],
            hojas_base
        )

        costo_material = float(df_val["Costo"].sum())

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
        # 4) PRECIO (SIN DEPENDENCIA EXTERNA)
        # -------------------------------------------------
        precio_unitario = costo_total * (1 + margen_utilidad)

        if precio_unitario <= 0:
            raise ValueError(f"Estructura sin precio: {cod}")

        filas.append({
            "codigodeestructura": cod,
            "Cantidad": qty,
            "Costo Material": round(costo_material, 2),
            "Costo Operativo": round(costo_operativo, 2),
            "Costo Unitario": round(costo_total, 2),
            "Precio Unitario": round(precio_unitario, 2),
            "Total": round(precio_unitario * qty, 2),
        })

    return pd.DataFrame(filas)
