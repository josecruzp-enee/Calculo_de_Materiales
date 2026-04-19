# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from typing import Dict, Any

from materiales.calculos.calculo_estructuras import calcular_estructuras_proyecto


# =========================================================
# 🔧 UTILIDADES SEGURAS
# =========================================================
def _safe_sum(series: pd.Series) -> float:
    try:
        return float(pd.to_numeric(series, errors="coerce").fillna(0).sum())
    except Exception:
        return 0.0


# =========================================================
# 🔥 EXTRAER MÉTRICAS DE ESTRUCTURAS
# =========================================================
def _extraer_metricas_estructuras(df_estructuras_global: pd.DataFrame):

    if df_estructuras_global is None or df_estructuras_global.empty:
        return 0, 0, 0

    df = df_estructuras_global.copy()

    if "Estructura" not in df.columns or "Cantidad" not in df.columns:
        return 0, 0, 0

    df["Estructura"] = df["Estructura"].astype(str).str.upper()
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)

    total_estructuras = int(df["Cantidad"].sum())

    num_postes = int(
        df[df["Estructura"].str.startswith("PC", na=False)]["Cantidad"].sum()
    )

    num_retenidas = int(
        df[df["Estructura"].str.startswith("R-", na=False)]["Cantidad"].sum()
    )

    return total_estructuras, num_postes, num_retenidas


# =========================================================
# 🔥 EXTRAER LONGITUDES DE CABLE
# =========================================================
def _extraer_longitudes(df_cables: pd.DataFrame):

    if df_cables is None or df_cables.empty:
        return 0.0, 0.0

    df = df_cables.copy()

    if "Tipo" not in df.columns:
        return 0.0, 0.0

    df["Tipo"] = df["Tipo"].astype(str).str.upper()

    if "Total Cable (m)" in df.columns:
        df["Total Cable (m)"] = pd.to_numeric(df["Total Cable (m)"], errors="coerce").fillna(0)
        col_long = "Total Cable (m)"
    elif "Longitud" in df.columns:
        df["Longitud"] = pd.to_numeric(df["Longitud"], errors="coerce").fillna(0)
        col_long = "Longitud"
    else:
        return 0.0, 0.0

    primario = df[df["Tipo"].str.startswith("MT", na=False)]
    secundario = df[df["Tipo"].str.startswith("BT", na=False)]

    return float(primario[col_long].sum()), float(secundario[col_long].sum())


# =========================================================
# 🔥 VALIDAR MATERIALES
# =========================================================
def _validar_materiales(df_materiales_costos: pd.DataFrame):

    if df_materiales_costos is None or df_materiales_costos.empty:
        raise ValueError("No hay materiales con costos")

    if "Costo Total" not in df_materiales_costos.columns:
        raise ValueError("df_materiales_costos debe tener 'Costo Total'")


# =========================================================
# 🔥 MOTOR DE COSTOS REAL (YA SIN IMPORTS ROTOS)
# =========================================================
def _motor_costos(
    df_materiales,
    longitud_primario_m,
    longitud_secundario_m,
    total_estructuras,
    num_postes,
    num_retenidas,
    precio_total_proyecto,
):

    costo_materiales = float(df_materiales["Costo Total"].sum())

    dias_primario = longitud_primario_m / 500 if longitud_primario_m else 0
    dias_secundario = longitud_secundario_m / 300 if longitud_secundario_m else 0
    dias_estructura = total_estructuras / 8 if total_estructuras else 0

    dias_totales = dias_primario + dias_secundario + dias_estructura

    costo_cuadrilla = dias_totales * 10000

    total_agujeros = num_postes + num_retenidas
    costo_agujeros = total_agujeros * 500

    horas_grua = num_postes * 1 + (num_postes // 8) * 2
    costo_grua = horas_grua * 1500

    costo_enee = 35000

    subtotal = (
        costo_materiales
        + costo_cuadrilla
        + costo_agujeros
        + costo_grua
        + costo_enee
    )

    contingencia = subtotal * 0.05

    costo_total_real = subtotal + contingencia

    utilidad = precio_total_proyecto - costo_total_real

    margen_pct = (utilidad / precio_total_proyecto * 100) if precio_total_proyecto else 0

    return {
        "costo_materiales": costo_materiales,
        "costo_cuadrilla": costo_cuadrilla,
        "costo_agujeros": costo_agujeros,
        "costo_grua": costo_grua,
        "costo_enee": costo_enee,
        "contingencia": contingencia,
        "costo_total_real": costo_total_real,
        "precio_venta": precio_total_proyecto,
        "utilidad": utilidad,
        "margen_pct": round(margen_pct, 2),
        "dias_totales": round(dias_totales, 2),
        "num_postes": num_postes,
        "num_retenidas": num_retenidas,
        "total_estructuras": total_estructuras,
        "longitud_primario": longitud_primario_m,
        "longitud_secundario": longitud_secundario_m,
    }


# =========================================================
# 🔥 FUNCIÓN PRINCIPAL
# =========================================================
def calcular_costos_proyecto(entrada) -> Dict[str, Any]:

    try:

        res_estructuras = getattr(entrada, "resultado_estructuras", None)

        if res_estructuras is None:
            res_estructuras = calcular_estructuras_proyecto(entrada.df_estructuras)

        df_estructuras_global = res_estructuras.get("df_estructuras")

        total_estructuras, num_postes, num_retenidas = _extraer_metricas_estructuras(
            df_estructuras_global
        )

        longitud_primario, longitud_secundario = _extraer_longitudes(
            getattr(entrada, "df_cables", None)
        )

        df_materiales_costos = getattr(entrada, "df_materiales_costos", None)

        _validar_materiales(df_materiales_costos)

        df_precios = getattr(entrada, "df_precios_estructura", None)

        precio_total = _safe_sum(df_precios.get("Precio Total", 0)) if df_precios is not None else 0

        resultado = _motor_costos(
            df_materiales_costos,
            longitud_primario,
            longitud_secundario,
            total_estructuras,
            num_postes,
            num_retenidas,
            precio_total,
        )

        return {
            "ok": True,
            "resultado_costos_proyecto": resultado,
        }

    except Exception as e:

        return {
            "ok": False,
            "error": str(e),
            "resultado_costos_proyecto": None
        }
