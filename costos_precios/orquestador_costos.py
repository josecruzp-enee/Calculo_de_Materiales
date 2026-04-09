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
# CONTRATO
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
def _norm_str(x):
    return str(x).strip().upper()


def _normalizar_dataframes(df_ep, df_mp):
    df_ep = df_ep.copy()
    df_mp = df_mp.copy()

    df_ep["Punto"] = df_ep["Punto"].astype(str).str.strip().str.upper()
    df_mp["Punto"] = df_mp["Punto"].astype(str).str.strip().str.upper()

    df_ep["Estructura"] = df_ep["Estructura"].astype(str).str.strip().str.upper()
    df_ep["Cantidad"] = pd.to_numeric(df_ep["Cantidad"], errors="coerce").fillna(0)

    return df_ep, df_mp


def _mapear_punto_a_estructuras(df_ep):
    return (
        df_ep
        .groupby("Punto")["Estructura"]
        .apply(list)
        .to_dict()
    )


def _construir_bom(df_mp, map_punto_est, debug):
    df_materiales_por_estructura = {}
    puntos_sin_match = []

    for punto, df_p in df_mp.groupby("Punto"):

        estructuras = map_punto_est.get(punto, [])

        if not estructuras:
            puntos_sin_match.append(punto)
            continue

        df_temp = df_p[["Materiales", "Unidad", "Cantidad"]].copy()

        for est in estructuras:
            df_materiales_por_estructura.setdefault(est, []).append(df_temp)

    debug["puntos_sin_match"] = puntos_sin_match[:20]

    return df_materiales_por_estructura


def _consolidar_bom(df_materiales_por_estructura):
    out = {}

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

        out[est] = df_concat

    return out


def _validar_bom(df_ep, df_materiales_por_estructura, debug):
    estructuras_sin_material = []

    for est in df_ep["Estructura"].unique():
        if est not in df_materiales_por_estructura:
            estructuras_sin_material.append(est)

    debug["estructuras_sin_material"] = estructuras_sin_material

    if estructuras_sin_material:
        raise ValueError(
            f"Estructuras sin materiales: {estructuras_sin_material[:10]}"
        )


# =====================================================
# ORQUESTADOR
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

    df_ep, df_mp = _normalizar_dataframes(
        entrada.df_estructuras_por_punto,
        entrada.df_materiales_por_punto
    )

    # =====================================================
    # 🔍 DEBUG BASE
    # =====================================================
    debug["DEBUG_BASE"] = {
        "estructuras_por_punto_head": df_ep.head(5).to_dict(),
        "materiales_por_punto_head": df_mp.head(5).to_dict(),
        "filas_ep": len(df_ep),
        "filas_mp": len(df_mp),
        "estructuras_unicas": df_ep["Estructura"].unique().tolist()[:20]
    }

    # =====================================================
    # 🔍 DEBUG PRECIOS
    # =====================================================
    debug["DEBUG_PRECIOS"] = {
        "columnas": list(entrada.fuente_precios.columns),
        "preview": entrada.fuente_precios.head(5).to_dict(),
        "filas": len(entrada.fuente_precios)
    }

    # =====================================================
    # 1. COSTOS MATERIALES
    # =====================================================
    df_costos_materiales = calcular_costos_desde_resumen(
        entrada.df_resumen,
        entrada.fuente_precios
    )

    debug["DEBUG_COSTOS_MATERIALES"] = {
        "head": df_costos_materiales.head(5).to_dict(),
        "columnas": list(df_costos_materiales.columns),
        "total": float(df_costos_materiales.get("Costo Total", pd.Series([0])).sum())
    }

    # =====================================================
    # 2. MAPEO
    # =====================================================
    map_punto_est = _mapear_punto_a_estructuras(df_ep)

    debug["DEBUG_MAPEO"] = {
        "total_puntos": len(map_punto_est),
        "ejemplo": dict(list(map_punto_est.items())[:3])
    }

    # =====================================================
    # 3. BOM
    # =====================================================
    df_materiales_por_estructura = _construir_bom(
        df_mp, map_punto_est, debug
    )

    df_materiales_por_estructura = _consolidar_bom(
        df_materiales_por_estructura
    )

    # 🔍 DEBUG BOM (CRÍTICO)
    ejemplo_est = list(df_materiales_por_estructura.keys())[:1]

    debug["DEBUG_BOM"] = {
        "total_estructuras": len(df_materiales_por_estructura),
        "ejemplo_estructura": ejemplo_est,
        "ejemplo_materiales": df_materiales_por_estructura[ejemplo_est[0]].head(5).to_dict()
        if ejemplo_est else {}
    }

    # =====================================================
    # 4. VALIDACIÓN
    # =====================================================
    _validar_bom(df_ep, df_materiales_por_estructura, debug)

    # =====================================================
    # 5. COSTOS ESTRUCTURAS
    # =====================================================
    df_costos_estructuras = calcular_costos_por_estructura(
        df_estructuras=df_ep,
        df_materiales_por_estructura=df_materiales_por_estructura,
        df_precios_materiales=entrada.fuente_precios
    )

    # 🔍 DEBUG COSTOS ESTRUCTURAS
    debug["DEBUG_COSTOS_ESTRUCTURAS"] = {
        "columnas": list(df_costos_estructuras.columns),
        "head": df_costos_estructuras.head(5).to_dict(),
        "filas": len(df_costos_estructuras)
    }

    # =====================================================
    # 6. COSTOS POR PUNTO
    # =====================================================
    df_ep2 = df_ep.copy()

    if "codigodeestructura" not in df_ep2.columns:
        df_ep2["codigodeestructura"] = df_ep2["Estructura"]

    df_ep2 = df_ep2[["Punto", "codigodeestructura", "Cantidad"]]

    # 🔍 DEBUG INPUT FINAL
    debug["DEBUG_INPUT_COSTOS_PUNTO"] = {
        "df_ep2_head": df_ep2.head(5).to_dict(),
        "columnas": list(df_ep2.columns)
    }

    df_detalle, df_resumen_costos, df_resumen_precios = calcular_costos_por_punto(
        df_ep2,
        df_costos_estructuras
    )

    return {
        "ok": True,
        "df_costos_materiales": df_costos_materiales,
        "df_costos_estructuras": df_costos_estructuras,
        "df_costos_por_punto": df_detalle,
        "df_resumen_costos_punto": df_resumen_costos,
        "df_resumen_precios_punto": df_resumen_precios,
        "debug": debug
    }
