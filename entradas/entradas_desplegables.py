# -*- coding: utf-8 -*-
"""
entradas_desplegables.py

Entrada mediante listas desplegables (UI → dominio).
"""

from __future__ import annotations

from typing import Dict, Any, Tuple
import pandas as pd


# ==========================================================
# HELPERS
# ==========================================================
def _asegurar_dataframe(df) -> pd.DataFrame:
    """
    Garantiza que el objeto sea un DataFrame válido.
    """
    if isinstance(df, pd.DataFrame):
        return df.copy()
    return pd.DataFrame()


def _normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia nombres de columnas.
    """
    if df.empty:
        return df

    df.columns = df.columns.map(str).str.strip()
    return df


# ==========================================================
# MAIN
# ==========================================================
def cargar_desde_desplegables(
    datos_fuente: Dict[str, Any]
) -> Tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Entrada desde UI (listas desplegables).
    """

    # =========================
    # Datos proyecto
    # =========================
    datos_proyecto = dict(datos_fuente.get("datos_proyecto") or {})

    # =========================
    # DataFrames
    # =========================
    df_estructuras = _asegurar_dataframe(datos_fuente.get("df_estructuras"))
    df_cables = _asegurar_dataframe(datos_fuente.get("df_cables"))
    df_materiales_extra = _asegurar_dataframe(datos_fuente.get("df_materiales_extra"))

    # =========================
    # Normalización básica
    # =========================
    df_estructuras = _normalizar_columnas(df_estructuras)
    df_cables = _normalizar_columnas(df_cables)
    df_materiales_extra = _normalizar_columnas(df_materiales_extra)

    return datos_proyecto, df_estructuras, df_cables, df_materiales_extra
