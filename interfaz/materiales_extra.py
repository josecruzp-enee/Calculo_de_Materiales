# -*- coding: utf-8 -*-
# interfaz/materiales_extra.py

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
# OPERACIONES
# =========================================================
def agregar_material(nombre: str, unidad: str, cantidad: float):

    if not nombre or float(cantidad) <= 0:
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


def consolidar_materiales(df: pd.DataFrame | None = None) -> pd.DataFrame:

    if df is None:
        df = st.session_state.get("materiales_extra", pd.DataFrame(columns=COLUMNAS))

    if df is None or df.empty:
        return pd.DataFrame(columns=COLUMNAS)

    df = df.copy()

    df["Materiales"] = df["Materiales"].astype(str).str.strip()
    df["Unidad"] = df["Unidad"].astype(str).str.strip()
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)

    df = df[df["Cantidad"] > 0]

    return (
        df.groupby(["Materiales", "Unidad"], as_index=False)
        .agg({"Cantidad": "sum"})
    )


def limpiar_materiales():
    st.session_state["materiales_extra"] = pd.DataFrame(columns=COLUMNAS)


# =========================================================
# EXPORT
# =========================================================
def obtener_materiales_finales() -> pd.DataFrame:

    df = consolidar_materiales()

    if df is None or df.empty:
        return pd.DataFrame(columns=COLUMNAS)

    return df.copy()
