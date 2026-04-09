# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from typing import Dict

from materiales.calculos.materiales_puntos import calcular_materiales_estructura
from costos_precios.costos_materiales import calcular_costos_desde_resumen


def calcular_costos_por_estructura(
    *,
    hojas_base: dict,
    conteo: Dict[str, int],
    tension_ll: float,
    calibre_mt: str,
    tabla_conectores_mt: pd.DataFrame,

    # 🔥 fuente de precios
    df_precios_materiales: pd.DataFrame,

    # 🔧 parámetros
    porcentaje_operativo: float = 0.25,
    margen_utilidad: float = 0.15,
) -> pd.DataFrame:

    # =====================================================
    # VALIDACIONES
    # =====================================================
    if not hojas_base:
        raise ValueError("hojas_base vacío")

    if not conteo:
        raise ValueError("conteo vacío")

    if df_precios_materiales is None or df_precios_materiales.empty:
        raise ValueError("df_precios_materiales inválido")

    filas = []

    # =====================================================
    # LOOP PRINCIPAL
    # =====================================================
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

        if df_mat is None or df_mat.empty:
            raise ValueError(f"Estructura sin materiales: {cod}")

        # -------------------------------------------------
        # 2) VALORIZACIÓN
        # -------------------------------------------------
        df_val = calcular_costos_desde_resumen(
            df_mat[["Materiales", "Unidad", "Cantidad"]],
            df_precios_materiales
        )

        # 🔥 VALIDACIÓN CRÍTICA
        if not df_val["Tiene_Precio"].all():
            faltantes = df_val.loc[
                ~df_val["Tiene_Precio"], "Materiales"
            ].unique()

            raise ValueError(
                f"Materiales sin precio en estructura {cod}: {list(faltantes)}"
            )

        # -------------------------------------------------
        # 3) COSTOS
        # -------------------------------------------------
        costo_material = float(
            pd.to_numeric(df_val["Costo"], errors="coerce").fillna(0).sum()
        )

        costo_operativo = costo_material * porcentaje_operativo

        costo_total = costo_material + costo_operativo

        # -------------------------------------------------
        # 4) PRECIO
        # -------------------------------------------------
        precio_unitario = costo_total * (1 + margen_utilidad)

        if precio_unitario <= 0:
            raise ValueError(f"Estructura sin precio: {cod}")

        # -------------------------------------------------
        # 5) SALIDA
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

    # =====================================================
    # OUTPUT
    # =====================================================
    return pd.DataFrame(filas)
