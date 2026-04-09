# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Union
import pandas as pd
from pathlib import Path

from costos_precios.costos_materiales import calcular_costos_desde_resumen
from costos_precios.costos_por_punto import calcular_costos_por_punto
from costos_precios.costos_estructuras import calcular_costos_por_estructura


# =====================================================
# CONTRATO (ALINEADO)
# =====================================================
@dataclass
class EntradaCostos:
    df_resumen: pd.DataFrame
    df_estructuras_por_punto: pd.DataFrame

    # 🔥 ahora sí alineado con builder
    df_materiales_por_estructura: Dict[str, pd.DataFrame] = field(default_factory=dict)

    fuente_precios: Union[pd.DataFrame, str, Path] = None


# =====================================================
# HELPERS
# =====================================================
def norm(x):
    return str(x).strip().upper()


# =====================================================
# ORQUESTADOR COSTOS
# =====================================================
def ejecutar_costos(entrada: EntradaCostos) -> Dict[str, Any]:

    debug = {}

    # =====================================================
    # VALIDACIONES
    # =====================================================
    if not isinstance(entrada.df_resumen, pd.DataFrame):
        raise TypeError("df_resumen inválido")

    if not isinstance(entrada.df_estructuras_por_punto, pd.DataFrame):
        raise TypeError("df_estructuras_por_punto inválido")

    if not isinstance(entrada.fuente_precios, pd.DataFrame):
        raise TypeError("fuente_precios inválida")

    if not isinstance(entrada.df_materiales_por_estructura, dict):
        raise TypeError("df_materiales_por_estructura inválido")

    df_ep = entrada.df_estructuras_por_punto.copy()

    debug["input"] = {
        "resumen_filas": len(entrada.df_resumen),
        "estructuras_filas": len(df_ep),
        "precios_filas": len(entrada.fuente_precios),
        "bom_estructuras": len(entrada.df_materiales_por_estructura),
        "columnas_estructuras": list(df_ep.columns),
    }

    # =====================================================
    # 1. COSTOS MATERIALES
    # =====================================================
    df_costos_materiales = calcular_costos_desde_resumen(
        entrada.df_resumen,
        entrada.fuente_precios
    )

    if df_costos_materiales is None or df_costos_materiales.empty:
        raise ValueError("No hay match entre materiales y precios")

    debug["materiales"] = {
        "filas": len(df_costos_materiales),
        "total": float(df_costos_materiales["Costo Total"].sum())
    }

    # =====================================================
    # 2. NORMALIZAR ESTRUCTURAS
    # =====================================================
    if "Estructura" not in df_ep.columns:
        raise ValueError("df_estructuras_por_punto no tiene columna Estructura")

    df_ep["Estructura"] = df_ep["Estructura"].apply(norm)
    df_ep["Cantidad"] = pd.to_numeric(df_ep["Cantidad"], errors="coerce").fillna(0)

    # =====================================================
    # 3. USAR BOM DESDE MATERIALES (FIX CLAVE)
    # =====================================================
    df_materiales_por_estructura = entrada.df_materiales_por_estructura

    if not df_materiales_por_estructura:
        raise ValueError("df_materiales_por_estructura vacío")

    debug["bom_total"] = len(df_materiales_por_estructura)

    # =====================================================
    # 4. COSTOS POR ESTRUCTURA
    # =====================================================
    df_costos_estructuras = calcular_costos_por_estructura(
        df_estructuras=df_ep,
        df_materiales_por_estructura=df_materiales_por_estructura,
        df_precios_materiales=entrada.fuente_precios
    )

    debug["estructuras"] = {
        "filas": len(df_costos_estructuras)
    }

    # =====================================================
    # 5. COSTOS POR PUNTO
    # =====================================================
    df_ep2 = df_ep.copy()

    if "codigodeestructura" not in df_ep2.columns:
        df_ep2["codigodeestructura"] = df_ep2["Estructura"]

    df_ep2 = df_ep2[["Punto", "codigodeestructura", "Cantidad"]]

    df_detalle, df_resumen_costos, df_resumen_precios = calcular_costos_por_punto(
        df_ep2,
        df_costos_estructuras
    )

    debug["puntos"] = {
        "filas": len(df_detalle)
    }

    # =====================================================
    # OUTPUT
    # =====================================================
    return {
        "ok": True,
        "df_costos_materiales": df_costos_materiales,
        "df_costos_estructuras": df_costos_estructuras,
        "df_costos_por_punto": df_detalle,
        "df_resumen_costos_punto": df_resumen_costos,
        "df_resumen_precios_punto": df_resumen_precios,
        "debug": debug
    }
