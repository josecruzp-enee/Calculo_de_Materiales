# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from costos_precios.costos_operativos import calcular_costos_operativos
from costos_precios.precio_estructura import calcular_precio_estructura


# =========================================================
# ORQUESTADOR DE PRECIOS POR ESTRUCTURA
# =========================================================
# =========================================================
# ORQUESTADOR DE PRECIOS POR ESTRUCTURA (CORREGIDO)
# =========================================================
def calcular_precios_por_estructura(
    df_costos_estructura: pd.DataFrame,
    df_estructuras: pd.DataFrame,
    df_mano_obra: pd.DataFrame,  # 🔥 NUEVO
    *,
    porcentaje_utilidad: float = 0.15,
):

    # =====================================================
    # VALIDACIONES
    # =====================================================
    if df_costos_estructura is None or df_costos_estructura.empty:
        raise ValueError("df_costos_estructura vacío")

    if df_estructuras is None or df_estructuras.empty:
        raise ValueError("df_estructuras vacío")

    if df_mano_obra is None or df_mano_obra.empty:
        raise ValueError("df_mano_obra vacío")

    # =====================================================
    # TOTALES DEL PROYECTO
    # =====================================================
    material_total = df_costos_estructura["Costo Total"].sum()
    mo_total = df_mano_obra["MO Total"].sum()

    # 🔥 COSTOS OPERATIVOS GLOBAL
    costos_op = calcular_costos_operativos(
        costo_material_total=material_total,
        costo_mano_obra=mo_total
    )

    # =====================================================
    # CANTIDADES
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
        costo_material_unit = float(r["Costo Unitario"])
        costo_material_total_estructura = float(r["Costo Total"])
        cantidad = max(1, int(r["Cantidad"]))

        # -------------------------------------------------
        # PESO DE LA ESTRUCTURA
        # -------------------------------------------------
        if material_total <= 0:
            continue

        peso = costo_material_total_estructura / material_total

        # -------------------------------------------------
        # COSTO OPERATIVO DISTRIBUIDO
        # -------------------------------------------------
        costo_operativo_unitario = (
            costos_op.operativo_total * peso
        ) / cantidad

        # -------------------------------------------------
        # PRECIO FINAL
        # -------------------------------------------------
        precio = calcular_precio_estructura(
            estructura=estructura,
            costo_materiales=costo_material_unit,
            costo_operativo=costo_operativo_unitario,
            porcentaje_utilidad=porcentaje_utilidad,
        )

        cantidad_real = cantidades.get(precio.estructura, 0)

        if cantidad_real <= 0:
            continue

        subtotal = precio.precio_unitario * cantidad_real
        total_base += subtotal

        filas.append({
            "Estructura": precio.estructura,
            "Cantidad": cantidad_real,
            "Precio Unitario": precio.precio_unitario,
            "Subtotal": subtotal,
        })

    df_out = pd.DataFrame(filas)

    if df_out.empty:
        raise ValueError("No se generaron precios de estructura")

    return df_out, total_base
