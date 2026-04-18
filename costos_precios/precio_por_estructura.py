# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd


# =========================================================
# COSTOS OPERATIVOS
# =========================================================
def calcular_costos_operativos(
    *,
    costo_material_total: float,
    costo_mano_obra: float,
    factor_equipos: float = 0.05,
    factor_logistica: float = 0.15,
):

    equipos = costo_material_total * factor_equipos
    logistica = costo_material_total * factor_logistica

    operativo_total = costo_mano_obra + equipos + logistica

    return {
        "equipos": round(equipos, 2),
        "logistica": round(logistica, 2),
        "operativo_total": round(operativo_total, 2),
    }


# =========================================================
# PRECIO TÉCNICO (SIN CONTROL)
# =========================================================
def calcular_precio_estructura(
    *,
    estructura: str,
    costo_materiales: float,
    costo_operativo: float,
    porcentaje_utilidad: float,
):

    costo_base = costo_materiales + costo_operativo
    precio = costo_base * (1 + porcentaje_utilidad)

    return {
        "estructura": estructura,
        "precio_unitario": round(precio, 2)
    }


# =========================================================
# 🔥 ACOTAMIENTO COMERCIAL (CLAVE)
# =========================================================
def acotar_precio_comercial(codigo: str, precio: float) -> float:

    codigo = str(codigo).upper()

    # PRIMARIO
    if codigo.startswith("A-I"):
        return max(1500, min(precio, 2000))

    if codigo.startswith("A-II"):
        return max(3000, min(precio, 4000))

    if codigo.startswith("A-III"):
        return max(5000, min(precio, 6000))

    # SECUNDARIO
    if codigo.startswith("B-I"):
        return max(800, min(precio, 1300))

    if codigo.startswith("B-II") or codigo.startswith("B-III"):
        return max(1200, min(precio, 1800))

    # RETENIDAS
    if codigo.startswith("R"):
        return max(1500, min(precio, 2500))

    # TIERRA
    if codigo.startswith("CT"):
        return 1500

    # CUCHILLAS
    if codigo.startswith("CS") or codigo.startswith("CA"):
        return min(precio, 3000)

    return precio


# =========================================================
# ORQUESTADOR PRINCIPAL
# =========================================================
def calcular_precios_por_estructura(
    df_costos_estructura: pd.DataFrame,
    df_estructuras: pd.DataFrame,
    df_mano_obra: pd.DataFrame,
    *,
    porcentaje_utilidad: float = 0.15,
):

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

        if material_total <= 0:
            continue

        # PESO DE LA ESTRUCTURA
        peso = costo_material_total_estructura / material_total

        # COSTO OPERATIVO DISTRIBUIDO
        costo_operativo_unitario = (
            costos_op["operativo_total"] * peso
        ) / cantidad

        # PRECIO TÉCNICO
        precio = calcular_precio_estructura(
            estructura=estructura,
            costo_materiales=costo_material_unit,
            costo_operativo=costo_operativo_unitario,
            porcentaje_utilidad=porcentaje_utilidad,
        )

        # 🔥 AJUSTE COMERCIAL FINAL
        precio_unitario = acotar_precio_comercial(
            estructura,
            precio["precio_unitario"]
        )

        cantidad_real = cantidades.get(estructura, 0)

        if cantidad_real <= 0:
            continue

        subtotal = precio_unitario * cantidad_real
        total_base += subtotal

        filas.append({
            "Estructura": estructura,
            "Cantidad": cantidad_real,
            "Precio Unitario": precio_unitario,
            "Subtotal": round(subtotal, 2),
        })

    df_out = pd.DataFrame(filas)

    if df_out.empty:
        raise ValueError("No se generaron precios de estructura")

    return df_out, round(total_base, 2)
