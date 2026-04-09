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
    df_materiales_por_estructura: Dict[str, pd.DataFrame]
    fuente_precios: Union[pd.DataFrame, str, Path]


def norm(x):
    return str(x).strip().upper()


def ejecutar_costos(entrada: EntradaCostos) -> Dict[str, Any]:

    debug = {}

    if not isinstance(entrada.df_resumen, pd.DataFrame):
        raise TypeError("df_resumen inválido")

    if not isinstance(entrada.df_estructuras_por_punto, pd.DataFrame):
        raise TypeError("df_estructuras_por_punto inválido")

    if not isinstance(entrada.fuente_precios, pd.DataFrame):
        raise TypeError("fuente_precios inválida")

    df_ep = entrada.df_estructuras_por_punto.copy()

    debug["input"] = {
        "resumen_filas": len(entrada.df_resumen),
        "estructuras_filas": len(df_ep),
        "precios_filas": len(entrada.fuente_precios),
        "columnas_estructuras": list(df_ep.columns),
    }

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

    if "Estructura" not in df_ep.columns:
        raise ValueError("df_estructuras_por_punto no tiene columna Estructura")

    df_ep["Estructura"] = df_ep["Estructura"].apply(norm)
    df_ep["Materiales"] = df_ep["Materiales"].astype(str).str.strip()
    df_ep["Unidad"] = df_ep["Unidad"].astype(str).str.strip()
    df_ep["Cantidad"] = pd.to_numeric(df_ep["Cantidad"], errors="coerce").fillna(0)

    df_materiales_por_estructura = {}

    for est in df_ep["Estructura"].unique():

        df_temp = df_ep[df_ep["Estructura"] == est][
            ["Materiales", "Unidad", "Cantidad"]
        ].copy()

        df_materiales_por_estructura[norm(est)] = df_temp

        debug.setdefault("bom", {})[est] = {"filas": len(df_temp)}

    debug["bom_total"] = len(df_materiales_por_estructura)

    df_costos_estructuras = calcular_costos_por_estructura(
        df_estructuras=df_ep,
        df_materiales_por_estructura=df_materiales_por_estructura,
        df_precios_materiales=entrada.fuente_precios
    )

    debug["estructuras"] = {"filas": len(df_costos_estructuras)}

    df_ep2 = df_ep.copy()

    if "codigodeestructura" not in df_ep2.columns:
        df_ep2["codigodeestructura"] = df_ep2["Estructura"]

    df_ep2 = df_ep2[["Punto", "codigodeestructura", "Cantidad"]]

    df_detalle, df_resumen_costos, df_resumen_precios = calcular_costos_por_punto(
        df_ep2,
        df_costos_estructuras
    )

    debug["puntos"] = {"filas": len(df_detalle)}

    return {
        "ok": True,
        "df_costos_materiales": df_costos_materiales,
        "df_costos_estructuras": df_costos_estructuras,
        "df_costos_por_punto": df_detalle,
        "df_resumen_costos_punto": df_resumen_costos,
        "df_resumen_precios_punto": df_resumen_precios,
        "debug": debug
    }
