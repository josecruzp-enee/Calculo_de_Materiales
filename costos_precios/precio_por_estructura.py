# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from costos_precios.costos_operativos import calcular_costos_operativos
from costos_precios.precio_estructura import calcular_precio_estructura


# =========================================================
# ORQUESTADOR DE PRECIOS POR ESTRUCTURA
# =========================================================
def calcular_precios_por_estructura(
    df_costos_estructura: pd.DataFrame,
    *,
    porcentaje_utilidad: float = 0.15,
    costo_cuadrilla_dia: float = 10000,
    fraccion_jornada: float = 1/16,
) -> pd.DataFrame:
    """
    Genera el precio unitario completo por cada tipo de estructura.

    INPUT:
    - df_costos_estructura:
        columnas esperadas:
            - codigodeestructura
            - Costo Unitario

    OUTPUT:
    - DataFrame con:
        - Estructura
        - Costo Materiales
        - Costo Operativo
        - Costo Base
        - Utilidad
        - Precio Unitario
    """

    # =====================================================
    # VALIDACIONES
    # =====================================================
    if df_costos_estructura is None or not isinstance(df_costos_estructura, pd.DataFrame):
        raise ValueError("df_costos_estructura inválido")

    if df_costos_estructura.empty:
        raise ValueError("df_costos_estructura vacío")

    required_cols = ["codigodeestructura", "Costo Unitario"]
    faltantes = [c for c in required_cols if c not in df_costos_estructura.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas en df_costos_estructura: {faltantes}")

    # =====================================================
    # PROCESO
    # =====================================================
    filas = []

    for _, r in df_costos_estructura.iterrows():

        estructura = str(r["codigodeestructura"]).strip()
        costo_material = float(r["Costo Unitario"])

        # =================================================
        # COSTOS OPERATIVOS (REGLAS DEFINIDAS)
        # =================================================
        costo_equipos = costo_material * 0.05
        costo_logistica = costo_material * 0.15

        costos_op = calcular_costos_operativos(
            costo_cuadrilla_dia=costo_cuadrilla_dia,
            fraccion_jornada=fraccion_jornada,
            costo_equipos=costo_equipos,
            costo_logistica=costo_logistica,
        )

        # =================================================
        # PRECIO FINAL
        # =================================================
        precio = calcular_precio_estructura(
            estructura=estructura,
            costo_materiales=costo_material,
            costo_operativo=costos_op.operativo_total,
            porcentaje_utilidad=porcentaje_utilidad,
        )

        # =================================================
        # OUTPUT
        # =================================================
        filas.append({
            "Estructura": precio.estructura,
            "Costo Materiales": precio.costo_materiales,
            "Costo Operativo": precio.costo_operativo,
            "Costo Base": precio.costo_base,
            "Utilidad": precio.utilidad,
            "Precio Unitario": precio.precio_unitario,
        })

    return pd.DataFrame(filas)
