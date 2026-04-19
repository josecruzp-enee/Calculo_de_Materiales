# -*- coding: utf-8 -*-
from __future__ import annotations

import math
import pandas as pd
from typing import Dict, Any


# =========================================================
# CONFIGURACIÓN BASE
# =========================================================
COSTO_CUADRILLA_DIA = 10000
PRECIO_AGUJERO = 500
PRECIO_GRUA_HORA = 1500
COSTO_ENEE = 35000

FACTOR_IMPRODUCTIVO = 0.10
FACTOR_CONTINGENCIA = 0.05


# =========================================================
# UTILIDADES
# =========================================================
def _ceil(valor: float) -> int:
    return int(math.ceil(valor))


# =========================================================
# 1. COSTO DE MATERIALES
# =========================================================
def calcular_costo_materiales(df_materiales: pd.DataFrame) -> float:
    if df_materiales is None or df_materiales.empty:
        raise ValueError("df_materiales vacío o inválido")

    required = {"cantidad", "precio_unitario"}
    if not required.issubset(df_materiales.columns):
        raise ValueError(f"df_materiales debe contener: {required}")

    df = df_materiales.copy()

    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0)
    df["precio_unitario"] = pd.to_numeric(df["precio_unitario"], errors="coerce").fillna(0)

    df["subtotal"] = df["cantidad"] * df["precio_unitario"]

    return round(df["subtotal"].sum(), 2)


# =========================================================
# 2. TIEMPO DEL PROYECTO
# =========================================================
def calcular_tiempo_proyecto(
    longitud_primario_m: float,
    longitud_secundario_m: float,
    total_estructuras: int,
) -> Dict[str, Any]:

    dias_primario = _ceil(longitud_primario_m / 500) if longitud_primario_m > 0 else 0
    dias_secundario = _ceil(longitud_secundario_m / 300) if longitud_secundario_m > 0 else 0

    horas_estructura = total_estructuras * 1
    dias_estructura = _ceil(horas_estructura / 8) if horas_estructura > 0 else 0

    dias_base = dias_primario + dias_secundario + dias_estructura
    dias_totales = dias_base * (1 + FACTOR_IMPRODUCTIVO)

    return {
        "dias_primario": dias_primario,
        "dias_secundario": dias_secundario,
        "dias_estructura": dias_estructura,
        "dias_base": dias_base,
        "dias_totales": round(dias_totales, 2),
    }


# =========================================================
# 3. COSTOS OPERATIVOS
# =========================================================
def calcular_costos_operativos(
    dias_totales: float,
    num_postes: int,
    num_retenidas: int,
) -> Dict[str, float]:

    # 🔹 Cuadrilla
    costo_cuadrilla = dias_totales * COSTO_CUADRILLA_DIA

    # 🔹 Agujeros
    total_agujeros = num_postes + num_retenidas
    costo_agujeros = total_agujeros * PRECIO_AGUJERO

    # 🔹 Grúa
    horas_grua = (num_postes * 1) + (_ceil(num_postes / 8) * 2 if num_postes > 0 else 0)
    costo_grua = horas_grua * PRECIO_GRUA_HORA

    return {
        "costo_cuadrilla": round(costo_cuadrilla, 2),
        "costo_agujeros": round(costo_agujeros, 2),
        "costo_grua": round(costo_grua, 2),
        "horas_grua": horas_grua,
    }


# =========================================================
# 4. CONSOLIDACIÓN TOTAL
# =========================================================
def calcular_costos_proyecto(
    *,
    df_materiales: pd.DataFrame,
    longitud_primario_m: float,
    longitud_secundario_m: float,
    total_estructuras: int,
    num_postes: int,
    num_retenidas: int,
    precio_total_proyecto: float,
) -> Dict[str, Any]:

    # -----------------------------------------------------
    # MATERIALES
    # -----------------------------------------------------
    costo_materiales = calcular_costo_materiales(df_materiales)

    # -----------------------------------------------------
    # TIEMPO
    # -----------------------------------------------------
    tiempo = calcular_tiempo_proyecto(
        longitud_primario_m,
        longitud_secundario_m,
        total_estructuras,
    )

    # -----------------------------------------------------
    # COSTOS OPERATIVOS
    # -----------------------------------------------------
    costos_op = calcular_costos_operativos(
        tiempo["dias_totales"],
        num_postes,
        num_retenidas,
    )

    # -----------------------------------------------------
    # COSTO DIRECTO
    # -----------------------------------------------------
    costo_directo = (
        costo_materiales
        + costos_op["costo_cuadrilla"]
        + costos_op["costo_agujeros"]
        + costos_op["costo_grua"]
        + COSTO_ENEE
    )

    # -----------------------------------------------------
    # CONTINGENCIA
    # -----------------------------------------------------
    contingencia = costo_directo * FACTOR_CONTINGENCIA

    # -----------------------------------------------------
    # TOTAL REAL
    # -----------------------------------------------------
    costo_total_real = costo_directo + contingencia

    # -----------------------------------------------------
    # FINANCIERO
    # -----------------------------------------------------
    utilidad = precio_total_proyecto - costo_total_real
    margen = (utilidad / precio_total_proyecto) if precio_total_proyecto > 0 else 0

    return {
        # Tiempo
        **tiempo,

        # Costos
        "costo_materiales": round(costo_materiales, 2),
        "costo_cuadrilla": costos_op["costo_cuadrilla"],
        "costo_agujeros": costos_op["costo_agujeros"],
        "costo_grua": costos_op["costo_grua"],
        "costo_enee": COSTO_ENEE,
        "contingencia": round(contingencia, 2),

        # Totales
        "costo_total_real": round(costo_total_real, 2),
        "precio_venta": round(precio_total_proyecto, 2),
        "utilidad": round(utilidad, 2),
        "margen_pct": round(margen * 100, 2),
    }


# =========================================================
# 5. REPORTE TEXTO
# =========================================================
def generar_reporte(resultado: Dict[str, Any]) -> str:

    return f"""
---------------------------------
RESUMEN DEL PROYECTO
---------------------------------

Duración estimada:
    Primario:     {resultado['dias_primario']} días
    Secundario:   {resultado['dias_secundario']} días
    Estructuras:  {resultado['dias_estructura']} días
    TOTAL:        {resultado['dias_totales']} días

---------------------------------
COSTOS
---------------------------------

Materiales:       L {resultado['costo_materiales']:,.2f}
Cuadrilla:        L {resultado['costo_cuadrilla']:,.2f}
Agujeros:         L {resultado['costo_agujeros']:,.2f}
Grúa:             L {resultado['costo_grua']:,.2f}
ENEE:             L {resultado['costo_enee']:,.2f}
Contingencia:     L {resultado['contingencia']:,.2f}

---------------------------------
COSTO TOTAL REAL: L {resultado['costo_total_real']:,.2f}

PRECIO VENTA:     L {resultado['precio_venta']:,.2f}

---------------------------------
UTILIDAD:         L {resultado['utilidad']:,.2f}
MARGEN:           {resultado['margen_pct']} %
---------------------------------
"""


# =========================================================
# EJEMPLO DE USO (BORRAR EN PRODUCCIÓN)
# =========================================================
if __name__ == "__main__":

    df_materiales = pd.DataFrame({
        "item": ["Poste", "Cable", "Herrajes"],
        "cantidad": [10, 500, 20],
        "precio_unitario": [9000, 50, 200],
    })

    resultado = calcular_costos_proyecto(
        df_materiales=df_materiales,
        longitud_primario_m=1000,
        longitud_secundario_m=600,
        total_estructuras=40,
        num_postes=10,
        num_retenidas=8,
        precio_total_proyecto=250000,
    )

    print(generar_reporte(resultado))
