# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Union
import pandas as pd
from pathlib import Path

# =====================================================
# COSTOS BASE
# =====================================================
from costos_precios.costos_materiales import calcular_costos_desde_resumen
from costos_precios.costos_por_punto import calcular_costos_por_punto


# =====================================================
# CONTRATO FUERTE
# =====================================================
@dataclass
class EntradaCostos:
    df_resumen: pd.DataFrame
    df_estructuras_por_punto: pd.DataFrame
    df_costos_estructuras: pd.DataFrame
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
            raise ValueError(
                f"{nombre} no tiene columnas requeridas: {faltantes}. "
                f"Columnas actuales: {list(df.columns)}"
            )


def _validar_fuente_precios(fuente: Union[pd.DataFrame, str, Path]):
    if fuente is None:
        raise ValueError("fuente_precios es requerido")

    # DataFrame
    if isinstance(fuente, pd.DataFrame):
        if fuente.empty:
            raise ValueError("df_precios_materiales está vacío")
        return fuente

    # Ruta
    if isinstance(fuente, (str, Path)):
        ruta = Path(fuente)
        if not ruta.exists():
            raise FileNotFoundError(f"Archivo de precios no existe: {ruta}")
        return ruta

    raise TypeError("fuente_precios debe ser DataFrame o ruta válida")


# =====================================================
# ORQUESTADOR COSTOS (PRO)
# =====================================================
def ejecutar_costos(entrada: EntradaCostos) -> Dict[str, Any]:
    """
    Orquestador de dominio de costos.

    ✔ Valida inputs
    ✔ Calcula costos de materiales
    ✔ Calcula costos por punto
    ✔ Consolida resultados

    ❌ No calcula materiales
    ❌ No transforma estructuras
    """

    # =====================================================
    # VALIDACIÓN DE CONTRATO
    # =====================================================
    if not isinstance(entrada, EntradaCostos):
        raise TypeError("entrada debe ser EntradaCostos")

    # =====================================================
    # VALIDACIÓN DATAFRAMES
    # =====================================================
    _validar_df(
        "df_resumen",
        entrada.df_resumen,
        cols_minimas=["materiales", "cantidad"]
    )

    _validar_df("df_estructuras_por_punto", entrada.df_estructuras_por_punto)
    cols_ep = _cols_norm(entrada.df_estructuras_por_punto)

    if not ({"estructura", "codigodeestructura", "punto"} & cols_ep):
        raise ValueError(
            "df_estructuras_por_punto debe contener alguna de: "
            "estructura / codigodeestructura / punto"
        )

    _validar_df(
        "df_costos_estructuras",
        entrada.df_costos_estructuras,
        cols_minimas=["estructura"]
    )

    fuente_precios = _validar_fuente_precios(entrada.fuente_precios)

    # =====================================================
    # 1. COSTOS DE MATERIALES
    # =====================================================
    df_costos_materiales = calcular_costos_desde_resumen(
        entrada.df_resumen,
        fuente_precios
    )

    if df_costos_materiales is None or not isinstance(df_costos_materiales, pd.DataFrame):
        raise RuntimeError("calcular_costos_desde_resumen retornó inválido")

    if df_costos_materiales.empty:
        raise ValueError("df_costos_materiales vacío (sin match de precios)")

    # =====================================================
    # 2. COSTOS POR PUNTO
    # =====================================================
    out = calcular_costos_por_punto(
        entrada.df_estructuras_por_punto,
        entrada.df_costos_estructuras
    )

    if not isinstance(out, (tuple, list)) or len(out) != 3:
        raise RuntimeError(
            "calcular_costos_por_punto debe retornar (detalle, resumen_costos, resumen_precios)"
        )

    df_detalle, df_resumen_costos, df_resumen_precios = out

    # Validación fuerte de outputs
    for nombre, df_ in {
        "df_costos_por_punto": df_detalle,
        "df_resumen_costos_punto": df_resumen_costos,
        "df_resumen_precios_punto": df_resumen_precios,
    }.items():
        if df_ is None or not isinstance(df_, pd.DataFrame):
            raise RuntimeError(f"{nombre} inválido")

    # =====================================================
    # OUTPUT NORMALIZADO
    # =====================================================
    return {
        "ok": True,

        # 🔹 materiales
        "df_costos_materiales": df_costos_materiales,

        # 🔹 estructuras
        "df_costos_estructuras": entrada.df_costos_estructuras,

        # 🔹 detalle
        "df_costos_por_punto": df_detalle,
        "df_resumen_costos_punto": df_resumen_costos,
        "df_resumen_precios_punto": df_resumen_precios,
    }
