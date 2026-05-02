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

    # =========================
    # session_state
    # =========================
    if datos_fuente is None:
        try:
            import streamlit as st
            datos_fuente = st.session_state
        except Exception:
            datos_fuente = {}

    df = datos_fuente.get("df_estructuras")

    if not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(), None

    # =========================
    # 🔥 CLAVE: convertir a texto tipo DXF
    # =========================
    textos = []

    for _, row in df.iterrows():

        punto = str(row.get("Punto", "")).strip()
        if not punto:
            continue

        partes = [punto]

        for col in df.columns:
            if col == "Punto":
                continue

            val = row[col]

            if pd.notna(val) and val:
                partes.append(f"{val} (P)")  # ← clave

        textos.append(" ".join(partes))

    df_out = pd.DataFrame({"texto": textos})

    return df_out, None
