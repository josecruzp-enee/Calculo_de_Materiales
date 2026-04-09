# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Union
import pandas as pd
from pathlib import Path

from costos_precios.costos_materiales import calcular_costos_desde_resumen
from costos_precios.costos_por_punto import calcular_costos_por_punto


# =====================================================
# CONTRATO
# =====================================================
@dataclass
class EntradaCostos:
    df_resumen: pd.DataFrame
    df_estructuras_por_punto: pd.DataFrame
    df_costos_estructuras: pd.DataFrame  # ← ya no obligatorio como input real
    fuente_precios: Union[pd.DataFrame, str, Path]


# =====================================================
# HELPERS
# =====================================================
def _cols_norm(df: pd.DataFrame) -> set:
    return {str(c).strip().lower() for c in df.columns}


def _validar_df(nombre: str, df: pd.DataFrame, cols_minimas=None):
    if df is None or not isinstance(df, pd.DataFrame):
        raise TypeError(f"{nombre} debe ser DataFrame")

    if df.empty:
        raise ValueError(f"{nombre} está vacío")

    if cols_minimas:
        cols = _cols_norm(df)
        faltantes = [c for c in cols_minimas if c not in cols]
        if faltantes:
            raise ValueError(f"{nombre} no tiene columnas requeridas: {faltantes}")


def _validar_fuente_precios(fuente):
    if not isinstance(fuente, pd.DataFrame) or fuente.empty:
        raise ValueError("fuente_precios inválida")
    return fuente


# =====================================================
# ORQUESTADOR (LIMPIO)
# =====================================================
def ejecutar_costos(entrada: EntradaCostos) -> Dict[str, Any]:

    if not isinstance(entrada, EntradaCostos):
        raise TypeError("entrada debe ser EntradaCostos")

    # =====================================================
    # VALIDAR SOLO LO QUE VIENE DE FUERA
    # =====================================================
    _validar_df("df_resumen", entrada.df_resumen, ["materiales", "cantidad"])
    _validar_df("df_estructuras_por_punto", entrada.df_estructuras_por_punto)

    fuente_precios = _validar_fuente_precios(entrada.fuente_precios)

    # =====================================================
    # 1. COSTOS DE MATERIALES (UNITARIOS DEL EXCEL)
    # =====================================================
    df_costos_materiales = calcular_costos_desde_resumen(
        entrada.df_resumen,
        fuente_precios
    )

    if df_costos_materiales.empty:
        raise ValueError("No hay match entre materiales y precios")

    # =====================================================
    # 2. COSTOS POR ESTRUCTURA (SE CONSTRUYEN AQUÍ)
    # =====================================================
    df_costos_estructuras = (
        entrada.df_estructuras_por_punto[["Estructura"]]
        .drop_duplicates()
        .rename(columns={"Estructura": "estructura"})
        .copy()
    )

    df_costos_estructuras["costo"] = 0.0

    # =====================================================
    # 3. COSTOS POR PUNTO
    # =====================================================
    df_detalle, df_resumen_costos, df_resumen_precios = calcular_costos_por_punto(
        entrada.df_estructuras_por_punto,
        df_costos_estructuras
    )

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
    }
