# -*- coding: utf-8 -*-
"""
entradas_desplegables.py

Entrada mediante listas desplegables (UI → dominio).
VERSIÓN COMPATIBLE CON ORQUESTADOR ACTUAL
"""

from __future__ import annotations

from typing import Dict, Any, Tuple, Optional
import pandas as pd


# ==========================================================
# HELPERS
# ==========================================================
def _asegurar_dataframe(df) -> pd.DataFrame:
    if isinstance(df, pd.DataFrame):
        return df.copy()
    return pd.DataFrame()


def _normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df.columns = df.columns.map(str).str.strip()
    return df


# ==========================================================
# MAIN
# ==========================================================
def cargar_desde_desplegables(
    datos_fuente: Optional[Dict[str, Any]] = None
) -> Tuple[pd.DataFrame, None]:
    """
    Versión compatible con orquestador actual.

    Retorna:
        df_estructuras, ruta(None)
    """

    # =========================
    # Si no viene datos → usar session_state
    # =========================
    if datos_fuente is None:
        try:
            import streamlit as st
            datos_fuente = st.session_state
        except Exception:
            datos_fuente = {}

    # =========================
    # Obtener estructuras (principal)
    # =========================
    df_estructuras = _asegurar_dataframe(
        datos_fuente.get("df_estructuras")
    )

    df_estructuras = _normalizar_columnas(df_estructuras)

    # =========================
    # Retorno compatible
    # =========================
    return df_estructuras, None
