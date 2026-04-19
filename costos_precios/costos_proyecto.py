# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from typing import Dict, Any

from materiales.calculos.calculo_estructuras import calcular_estructuras_proyecto
from costos.motor_costos_proyecto import calcular_costos_proyecto


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

    # 🔥 USAR MISMA LÓGICA QUE PRECIOS
    if "Total Cable (m)" in df.columns:
        df["Total Cable (m)"] = pd.to_numeric(df["Total Cable (m)"], errors="coerce").fillna(0)
        col_long = "Total Cable (m)"
    elif "Longitud" in df.columns:
        df["Longitud"] = pd.to_numeric(df["Longitud"], errors="coerce").fillna(0)
        col_long = "Longitud"
    else:
        return 0.0, 0.0

    # 🔹 PRIMARIO
    primario = df[df["Tipo"].str.startswith("MT", na=False)]

    # 🔹 SECUNDARIO
    secundario = df[df["Tipo"].str.startswith("BT", na=False)]

    longitud_primario = float(primario[col_long].sum())
    longitud_secundario = float(secundario[col_long].sum())

    return longitud_primario, longitud_secundario

# =========================================================
# 🔥 VALIDAR MATERIALES
# =========================================================
def _validar_materiales(df_materiales_costos: pd.DataFrame):

    if df_materiales_costos is None or df_materiales_costos.empty:
        raise ValueError("No hay materiales con costos")

    if "Costo Total" not in df_materiales_costos.columns:
        raise ValueError(
            "df_materiales_costos debe tener 'Costo Total'. "
            "Usa calcular_lista_materiales_con_costos primero."
        )


# =========================================================
# 🔥 FUNCIÓN PRINCIPAL
# =========================================================
def calcular_costos_proyecto_integrado(entrada) -> Dict[str, Any]:

    try:

        # =====================================================
        # 1. ESTRUCTURAS (usar si ya vienen)
        # =====================================================
        res_estructuras = getattr(entrada, "resultado_estructuras", None)

        if res_estructuras is None:
            res_estructuras = calcular_estructuras_proyecto(
                entrada.df_estructuras
            )

        df_estructuras_global = res_estructuras.get("df_estructuras")

        total_estructuras, num_postes, num_retenidas = _extraer_metricas_estructuras(
            df_estructuras_global
        )

        # =====================================================
        # 2. CABLES
        # =====================================================
        longitud_primario, longitud_secundario = _extraer_longitudes(
            getattr(entrada, "df_cables", None)
        )

        # =====================================================
        # 3. MATERIALES (YA PROCESADOS)
        # =====================================================
        df_materiales_costos = getattr(entrada, "df_materiales_costos", None)

        _validar_materiales(df_materiales_costos)

        # =====================================================
        # 4. PRECIO ACTUAL (OPCIONAL)
        # =====================================================
        df_precios = getattr(entrada, "df_precios_estructura", None)

        if df_precios is not None and not df_precios.empty:
            precio_total = _safe_sum(df_precios.get("Precio Total", 0))
        else:
            precio_total = 0.0

        # =====================================================
        # 5. MOTOR DE COSTOS (OBRA REAL)
        # =====================================================
        resultado = calcular_costos_proyecto(
            df_materiales=df_materiales_costos,
            longitud_primario_m=longitud_primario,
            longitud_secundario_m=longitud_secundario,
            total_estructuras=total_estructuras,
            num_postes=num_postes,
            num_retenidas=num_retenidas,
            precio_total_proyecto=precio_total,
        )

        # =====================================================
        # 6. OUTPUT COMPLETO
        # =====================================================
        return {
            "ok": True,
            "resultado_costos_proyecto": resultado,
            "metricas": {
                "total_estructuras": total_estructuras,
                "num_postes": num_postes,
                "num_retenidas": num_retenidas,
                "longitud_primario": longitud_primario,
                "longitud_secundario": longitud_secundario,
                "precio_total": precio_total,
            }
        }

    except Exception as e:

        return {
            "ok": False,
            "error": str(e),
            "resultado_costos_proyecto": None
        }
