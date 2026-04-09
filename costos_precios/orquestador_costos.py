# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Union
import pandas as pd
from pathlib import Path

from costos_precios.costos_materiales import calcular_costos_desde_resumen
from costos_precios.costos_por_punto import calcular_costos_por_punto
from costos_precios.costos_estructuras import calcular_costos_por_estructura


# =====================================================
# CONTRATO (FINAL)
# =====================================================
@dataclass
class EntradaCostos:
    df_resumen: pd.DataFrame
    df_estructuras_por_punto: pd.DataFrame
    df_materiales_por_punto: pd.DataFrame
    fuente_precios: Union[pd.DataFrame, str, Path]


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

    if not isinstance(entrada.df_materiales_por_punto, pd.DataFrame):
        raise TypeError("df_materiales_por_punto inválido")

    if not isinstance(entrada.fuente_precios, pd.DataFrame):
        raise TypeError("fuente_precios inválida")

    df_ep = entrada.df_estructuras_por_punto.copy()
    df_mp = entrada.df_materiales_por_punto.copy()

    # =====================================================
    # DEBUG REAL
    # =====================================================
    debug["debug_costos"] = {
        "df_resumen_cols": list(entrada.df_resumen.columns),
        "df_ep_cols": list(df_ep.columns),
        "df_mp_cols": list(df_mp.columns),
        "filas_materiales": len(df_mp),
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
    # 3. MAPEO CLAVE (Punto → Estructura)
    # =====================================================
    map_punto_est = dict(zip(df_ep["Punto"], df_ep["Estructura"]))

    df_materiales_por_estructura = {}

    for punto, df_p in df_mp.groupby("Punto"):

        est = map_punto_est.get(punto)

        if est is None:
            continue

        df_temp = df_p[["Materiales", "Unidad", "Cantidad"]].copy()

        df_materiales_por_estructura.setdefault(est, []).append(df_temp)

    # =====================================================
    # CONSOLIDAR BOM
    # =====================================================
    for est, lista in df_materiales_por_estructura.items():

        df_concat = pd.concat(lista, ignore_index=True)

        df_concat["Cantidad"] = pd.to_numeric(
            df_concat["Cantidad"], errors="coerce"
        ).fillna(0)

        df_concat = (
            df_concat
            .groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"]
            .sum()
        )

        df_materiales_por_estructura[est] = df_concat

    if not df_materiales_por_estructura:
        raise ValueError("No se pudo construir BOM por estructura")

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
