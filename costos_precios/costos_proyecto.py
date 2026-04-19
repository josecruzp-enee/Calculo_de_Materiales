# -*- coding: utf-8 -*-
from __future__ import annotations

import math
import pandas as pd
from typing import Dict, Any


# =========================================================
# CONFIGURACIÓN
# =========================================================
COSTO_CUADRILLA_DIA = 10000
PRECIO_AGUJERO = 500
PRECIO_GRUA_HORA = 1500
COSTO_ENEE = 35000

FACTOR_IMPRODUCTIVO = 0.10
FACTOR_CONTINGENCIA = 0.05


# =========================================================
# UTILIDAD
# =========================================================
def _ceil(x: float) -> int:
    return int(math.ceil(x))


# =========================================================
# COSTO DE MATERIALES
# =========================================================
def calcular_costo_materiales(df_materiales: pd.DataFrame) -> float:

    if df_materiales is None or df_materiales.empty:
        return 0.0

    df = df_materiales.copy()

    # 🔥 normalización
    if "cantidad" not in df.columns:
        if "Cantidad" in df.columns:
            df["cantidad"] = df["Cantidad"]

    if "precio_unitario" not in df.columns:
        if "Precio Unitario" in df.columns:
            df["precio_unitario"] = df["Precio Unitario"]

    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0)
    df["precio_unitario"] = pd.to_numeric(df["precio_unitario"], errors="coerce").fillna(0)

    df["subtotal"] = df["cantidad"] * df["precio_unitario"]

    return float(df["subtotal"].sum())


# =========================================================
# MOTOR PRINCIPAL
# =========================================================
def calcular_costos_proyecto(
    *,
    df_materiales: pd.DataFrame,
    longitud_primario_m: float,
    longitud_secundario_m: float,
    total_estructuras: int,
    num_postes: int,
    num_retenidas: int,
    precio_total_proyecto: float = 0.0,
) -> Dict[str, Any]:

    # =====================================================
    # 1. TIEMPO
    # =====================================================
    dias_primario = _ceil(longitud_primario_m / 500) if longitud_primario_m > 0 else 0
    dias_secundario = _ceil(longitud_secundario_m / 300) if longitud_secundario_m > 0 else 0

    horas_estructura = total_estructuras * 1
    dias_estructura = _ceil(horas_estructura / 8) if horas_estructura > 0 else 0

    dias_base = dias_primario + dias_secundario + dias_estructura
    dias_totales = dias_base * (1 + FACTOR_IMPRODUCTIVO)

    # =====================================================
    # 2. COSTOS
    # =====================================================
    costo_materiales = calcular_costo_materiales(df_materiales)

    costo_cuadrilla = dias_totales * COSTO_CUADRILLA_DIA

    total_agujeros = num_postes + num_retenidas
    costo_agujeros = total_agujeros * PRECIO_AGUJERO

    horas_grua = (num_postes * 1) + (_ceil(num_postes / 8) * 2 if num_postes > 0 else 0)
    costo_grua = horas_grua * PRECIO_GRUA_HORA

    costo_directo = (
        costo_materiales
        + costo_cuadrilla
        + costo_agujeros
        + costo_grua
        + COSTO_ENEE
    )

    contingencia = costo_directo * FACTOR_CONTINGENCIA
    costo_total_real = costo_directo + contingencia

    # =====================================================
    # 3. RESULTADO FINANCIERO
    # =====================================================
    utilidad = precio_total_proyecto - costo_total_real
    margen = (utilidad / precio_total_proyecto) if precio_total_proyecto > 0 else 0

    # =====================================================
    # 4. SALIDA COMPLETA
    # =====================================================
    return {

        # 🔹 TIEMPO
        "dias_primario": dias_primario,
        "dias_secundario": dias_secundario,
        "dias_estructura": dias_estructura,
        "dias_totales": round(dias_totales, 2),

        # 🔹 COSTOS
        "costo_materiales": round(costo_materiales, 2),
        "costo_cuadrilla": round(costo_cuadrilla, 2),
        "costo_agujeros": round(costo_agujeros, 2),
        "costo_grua": round(costo_grua, 2),
        "costo_enee": COSTO_ENEE,
        "contingencia": round(contingencia, 2),

        # 🔹 RESULTADO
        "costo_total_real": round(costo_total_real, 2),
        "precio_venta": round(precio_total_proyecto, 2),
        "utilidad": round(utilidad, 2),
        "margen_pct": round(margen * 100, 2),

        # 🔥 DATOS DEL PROYECTO (PARA PDF)
        "total_estructuras": total_estructuras,
        "num_postes": num_postes,
        "num_retenidas": num_retenidas,
        "total_agujeros": total_agujeros,
        "longitud_primario": longitud_primario_m,
        "longitud_secundario": longitud_secundario_m,
    }


# =========================================================
# TEST RÁPIDO (OPCIONAL)
# =========================================================
if __name__ == "__main__":

    df = pd.DataFrame({
        "cantidad": [10, 100],
        "precio_unitario": [5000, 50],
    })

    res = calcular_costos_proyecto(
        df_materiales=df,
        longitud_primario_m=1000,
        longitud_secundario_m=500,
        total_estructuras=30,
        num_postes=10,
        num_retenidas=5,
        precio_total_proyecto=300000,
    )

    for k, v in res.items():
        print(k, ":", v)
