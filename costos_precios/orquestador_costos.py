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
    df_materiales_por_estructura: Dict[str, pd.DataFrame]  # 🔥 NUEVO
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
# ORQUESTADOR (CORRECTO)
# =====================================================
def ejecutar_costos(entrada: EntradaCostos) -> Dict[str, Any]:

    if not isinstance(entrada, EntradaCostos):
        raise TypeError("entrada debe ser EntradaCostos")

    # =====================================================
    # VALIDAR ENTRADAS
    # =====================================================
    _validar_df("df_resumen", entrada.df_resumen, ["materiales", "cantidad"])
    _validar_df("df_estructuras_por_punto", entrada.df_estructuras_por_punto)

    if not isinstance(entrada.df_materiales_por_estructura, dict):
        raise ValueError("df_materiales_por_estructura inválido")

    fuente_precios = _validar_fuente_precios(entrada.fuente_precios)

    # =====================================================
    # 1. COSTOS DE MATERIALES
    # =====================================================
    df_costos_materiales = calcular_costos_desde_resumen(
        entrada.df_resumen,
        fuente_precios
    )

    if df_costos_materiales.empty:
        raise ValueError("No hay match entre materiales y precios")

    # =====================================================
    # 2. COSTOS POR ESTRUCTURA (REAL)
    # =====================================================
    df_costos_estructuras = calcular_costos_por_estructura(
        df_estructuras=entrada.df_estructuras_por_punto,
        df_materiales_por_estructura=entrada.df_materiales_por_estructura,
        df_precios_materiales=fuente_precios
    )

    # =====================================================
    # 3. NORMALIZAR df_estructuras_por_punto
    # =====================================================
    df_ep = entrada.df_estructuras_por_punto.copy()

    if "codigodeestructura" not in df_ep.columns:
        if "Estructura" in df_ep.columns:
            df_ep["codigodeestructura"] = df_ep["Estructura"]
        else:
            raise ValueError("No existe columna codigodeestructura")

    df_ep = df_ep[["Punto", "codigodeestructura", "Cantidad"]]

    # =====================================================
    # 4. COSTOS POR PUNTO
    # =====================================================
    df_detalle, df_resumen_costos, df_resumen_precios = calcular_costos_por_punto(
        df_ep,
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
