# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


# =========================================================
# CONFIGURACIÓN
# =========================================================
USAR_BIBLIOTECA = True


# =========================================================
# BIBLIOTECA DE PRECIOS
# =========================================================
PRECIOS_BIBLIOTECA = {
    "A-I-1": 1500,
    "A-I-1V": 2000,
    "A-I-4": 1500,
    "A-I-4V": 2000,
    "A-I-6": 1800,

    "B-I-4D": 900,
    "B-III-1": 1200,
    "B-III-4": 1400,
    "B-III-6": 1600,

    "R-1": 1500,
    "R-3V": 1800,
    "R-4": 2200,
    "R-5T": 2500,

    "CT-N": 1500,

    "CS-2": 3000,
    "CA-32": 2500,
}


# =========================================================
# CONTRATO
# =========================================================
@dataclass(slots=True)
class ResultadoPrecioEstructura:
    estructura: str
    precio_unitario: float


# =========================================================
# COSTOS OPERATIVOS (SOLO INDIRECTOS)
# =========================================================
def calcular_costos_operativos(
    *,
    costo_material_total: float,
    factor_equipos: float = 0.05,
    factor_logistica: float = 0.15,
):

    equipos = costo_material_total * factor_equipos
    logistica = costo_material_total * factor_logistica

    return {
        "operativo_total": round(equipos + logistica, 2)
    }


# =========================================================
# MODELO DE PRECIO (OPCIONAL)
# =========================================================
def calcular_precio_estructura(
    *,
    estructura: str,
    costo_materiales: float,
    costo_operativo: float,
    porcentaje_utilidad: float,
) -> ResultadoPrecioEstructura:

    costo_base = costo_materiales + costo_operativo
    precio = costo_base * (1 + porcentaje_utilidad)

    return ResultadoPrecioEstructura(
        estructura=estructura.strip().upper(),
        precio_unitario=round(precio, 2)
    )


# =========================================================
# ORQUESTADOR
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
    # TOTALES
    # =====================================================
    material_total = df_costos_estructura["Costo Total"].sum()

    costos_op = calcular_costos_operativos(
        costo_material_total=material_total
    )

    # =====================================================
    # CANTIDADES
    # =====================================================
    df_tmp = df_estructuras.copy()
    df_tmp["Estructura"] = df_tmp["Estructura"].astype(str).str.strip().str.upper()
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

        estructura = str(r["codigodeestructura"]).strip().upper()
        costo_material_unit = float(r["Costo Unitario"])
        costo_material_total_estructura = float(r["Costo Total"])
        cantidad = max(1, int(r["Cantidad"]))

        if material_total <= 0:
            continue

        # DISTRIBUCIÓN OPERATIVA
        peso = costo_material_total_estructura / material_total

        costo_operativo_unitario = (
            costos_op["operativo_total"] * peso
        ) / cantidad

        # =================================================
        # 🔥 DECISIÓN: BIBLIOTECA O MODELO
        # =================================================
        if USAR_BIBLIOTECA:

            precio_unitario = PRECIOS_BIBLIOTECA.get(
                estructura,
                1500  # fallback
            )

        else:

            precio = calcular_precio_estructura(
                estructura=estructura,
                costo_materiales=costo_material_unit,
                costo_operativo=costo_operativo_unitario,
                porcentaje_utilidad=porcentaje_utilidad,
            )

            precio_unitario = precio.precio_unitario

        # =================================================
        # CANTIDAD REAL
        # =================================================
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
        raise ValueError("No se generaron precios")

    return df_out, round(total_base, 2)
