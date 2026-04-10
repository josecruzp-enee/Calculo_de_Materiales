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
    df_estructuras: pd.DataFrame,
    *,
    porcentaje_utilidad: float = 0.15,
    costo_cuadrilla_dia: float = 10000,
    fraccion_jornada: float = 1/16,
):
    """
    OUTPUT:
    - df_precios_estructura
    - total_base_proyecto
    """

    # =====================================================
    # VALIDACIONES
    # =====================================================
    if df_costos_estructura is None or not isinstance(df_costos_estructura, pd.DataFrame):
        raise ValueError("df_costos_estructura inválido")

    if df_costos_estructura.empty:
        raise ValueError("df_costos_estructura vacío")

    if df_estructuras is None or not isinstance(df_estructuras, pd.DataFrame):
        raise ValueError("df_estructuras inválido")

    if df_estructuras.empty:
        raise ValueError("df_estructuras vacío")

    required_cols = ["codigodeestructura", "Costo Unitario"]
    faltantes = [c for c in required_cols if c not in df_costos_estructura.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas en df_costos_estructura: {faltantes}")

    if "Estructura" not in df_estructuras.columns or "Cantidad" not in df_estructuras.columns:
        raise ValueError("df_estructuras debe tener 'Estructura' y 'Cantidad'")

    # =====================================================
    # NORMALIZAR CANTIDADES
    # =====================================================
    df_tmp = df_estructuras.copy()
    df_tmp["Estructura"] = df_tmp["Estructura"].astype(str).str.strip()
    df_tmp["Cantidad"] = pd.to_numeric(df_tmp["Cantidad"], errors="coerce").fillna(0)

    cantidades = (
        df_tmp.groupby("Estructura")["Cantidad"]
        .sum()
        .to_dict()
    )

    # =====================================================
    # PROCESO
    # =====================================================
    filas = []
    total_base = 0.0

    for _, r in df_costos_estructura.iterrows():

        estructura = str(r["codigodeestructura"]).strip()
        costo_material = float(r["Costo Unitario"])

        # -------------------------------------------------
        # COSTOS OPERATIVOS
        # -------------------------------------------------
        costo_equipos = costo_material * 0.05
        costo_logistica = costo_material * 0.15

        costos_op = calcular_costos_operativos(
            costo_cuadrilla_dia=costo_cuadrilla_dia,
            fraccion_jornada=fraccion_jornada,
            costo_equipos=costo_equipos,
            costo_logistica=costo_logistica,
        )

        # -------------------------------------------------
        # PRECIO FINAL
        # -------------------------------------------------
        precio = calcular_precio_estructura(
            estructura=estructura,
            costo_materiales=costo_material,
            costo_operativo=costos_op.operativo_total,
            porcentaje_utilidad=porcentaje_utilidad,
        )

        cantidad = cantidades.get(precio.estructura, 0)

        # 🔥 SI NO EXISTE EN PROYECTO, NO CONTAR
        if cantidad <= 0:
            continue

        subtotal = precio.precio_unitario * cantidad
        total_base += subtotal

        filas.append({
            "Estructura": precio.estructura,
            "Cantidad": cantidad,
            "Precio Unitario": precio.precio_unitario,
            "Subtotal": subtotal,
        })

    df_out = pd.DataFrame(filas)

    if df_out.empty:
        raise ValueError("No se generaron precios de estructura")

    return df_out, total_base
