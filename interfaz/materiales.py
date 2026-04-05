#esto es un legacy
# -*- coding: utf-8 -*-
# entradas/materiales.py
# Manejo de materiales extra desde UI + conexión con base de datos

from __future__ import annotations
import streamlit as st
import pandas as pd

COLUMNAS = ["Materiales", "Unidad", "Cantidad"]


# =========================================================
# ESTADO
# =========================================================

def inicializar_materiales_extra():
    if "materiales_extra" not in st.session_state:
        st.session_state["materiales_extra"] = pd.DataFrame(columns=COLUMNAS)


# =========================================================
# OPERACIONES UI
# =========================================================

def agregar_material(nombre: str, unidad: str, cantidad: float):
    if not nombre or cantidad <= 0:
        return

    df = st.session_state.get("materiales_extra", pd.DataFrame(columns=COLUMNAS))

    nuevo = pd.DataFrame([{
        "Materiales": str(nombre).strip(),
        "Unidad": str(unidad).strip(),
        "Cantidad": float(cantidad),
    }])

    st.session_state["materiales_extra"] = pd.concat(
        [df, nuevo], ignore_index=True
    )


def consolidar_materiales() -> pd.DataFrame:
    df = st.session_state.get("materiales_extra", pd.DataFrame(columns=COLUMNAS))

    if df.empty:
        return df

    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)

    return (
        df.groupby(["Materiales", "Unidad"], as_index=False)
        .agg({"Cantidad": "sum"})
    )


def limpiar_materiales():
    st.session_state["materiales_extra"] = pd.DataFrame(columns=COLUMNAS)


# =========================================================
# EXPORT / INTEGRACIÓN
# =========================================================

def obtener_materiales_finales() -> pd.DataFrame:
    """
    Devuelve materiales listos para integrarse al cálculo general.
    """
    return consolidar_materiales()
