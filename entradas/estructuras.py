# -*- coding: utf-8 -*-
# entradas/estructuras.py

from __future__ import annotations
import streamlit as st
import pandas as pd


# =========================================================
# ESTADO
# =========================================================

def inicializar_estado_estructuras():

    if "df_puntos" not in st.session_state:
        st.session_state["df_puntos"] = pd.DataFrame(
            columns=["Punto", "Estructuras"]
        )

    if "punto_en_edicion" not in st.session_state:
        st.session_state["punto_en_edicion"] = "Punto 1"


# =========================================================
# CATÁLOGO (ALINEADO CON UI)
# =========================================================

def obtener_opciones_catalogo():

    base = [
        "A-I-1",
        "A-I-4",
        "B-III-1",
        "B-III-5",
        "CT-N",
        "TS-50 KVA",
    ]

    return {
        "Poste": {"valores": base, "etiquetas": {}},
        "Primario": {"valores": base, "etiquetas": {}},
        "Secundario": {"valores": base, "etiquetas": {}},
        "Retenidas": {"valores": base, "etiquetas": {}},
        "Conexiones a tierra": {"valores": base, "etiquetas": {}},
        "Transformadores": {"valores": base, "etiquetas": {}},
        "Luminarias": {"valores": base, "etiquetas": {}},
    }


# =========================================================
# OPERACIONES
# =========================================================

def agregar_item_estructura(punto: str, estructura: str):

    df = st.session_state["df_puntos"]

    nueva_fila = pd.DataFrame([{
        "Punto": punto,
        "Estructuras": estructura
    }])

    st.session_state["df_puntos"] = pd.concat(
        [df, nueva_fila],
        ignore_index=True
    )


def eliminar_punto(punto):

    df = st.session_state["df_puntos"]

    df = df[df["Punto"] != punto]

    st.session_state["df_puntos"] = df.reset_index(drop=True)


def reset_estructuras():
    st.session_state["df_puntos"] = pd.DataFrame(
        columns=["Punto", "Estructuras"]
    )


def consolidar_punto(punto):

    df = st.session_state["df_puntos"]

    df_punto = df[df["Punto"] == punto]

    estructuras = df_punto["Estructuras"].tolist()

    return {
        "Punto": punto,
        "Estructuras": estructuras
    }


def construir_dataframe_salida():

    df = st.session_state.get("df_puntos")

    if df is None or df.empty:
        return pd.DataFrame(), None

    df_salida = (
        df.groupby("Punto")["Estructuras"]
        .apply(lambda x: "; ".join(x))
        .reset_index()
    )

    # 🔥 CLAVE: guardar para el flujo global
    st.session_state["df_estructuras"] = df_salida

    return df_salida, None


def crear_nuevo_punto():

    import streamlit as st
    import pandas as pd

    df = st.session_state.get("df_puntos", pd.DataFrame())

    # 🔥 obtener números reales de puntos existentes
    if df.empty or "Punto" not in df.columns:
        n = 1
    else:
        nums = (
            df["Punto"]
            .astype(str)
            .str.extract(r'(\d+)')[0]
            .dropna()
            .astype(int)
        )

        n = nums.max() + 1 if not nums.empty else 1

    # 🔥 formato estándar del sistema
    punto = f"P-{n:02d}"

    st.session_state["punto_en_edicion"] = punto
