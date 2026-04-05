# entradas/estructuras.py
# FACHADA PARA UI DE ESTRUCTURAS

from __future__ import annotations
import streamlit as st
import pandas as pd

from entradas.orquestador_entradas import cargar_entrada


# =========================================================
# ESTADO
# =========================================================

def inicializar_estado_estructuras():
    if "df_puntos" not in st.session_state:
        st.session_state["df_puntos"] = pd.DataFrame()

    if "punto_en_edicion" not in st.session_state:
        st.session_state["punto_en_edicion"] = "Punto 1"


# =========================================================
# CATÁLOGO (SIMPLIFICADO)
# =========================================================

def obtener_opciones_catalogo():
    return {
        "Poste": {"valores": [], "etiquetas": {}},
        "Primario": {"valores": [], "etiquetas": {}},
        "Secundario": {"valores": [], "etiquetas": {}},
        "Retenidas": {"valores": [], "etiquetas": {}},
        "Conexiones a tierra": {"valores": [], "etiquetas": {}},
        "Transformadores": {"valores": [], "etiquetas": {}},
        "Luminarias": {"valores": [], "etiquetas": {}},
    }


# =========================================================
# OPERACIONES
# =========================================================

def agregar_item_estructura(cat, sel, qty):
    pass


def consolidar_punto(punto):
    return {"Punto": punto}


def eliminar_punto(punto):
    pass


def reset_estructuras():
    st.session_state["df_puntos"] = pd.DataFrame()


def construir_dataframe_salida(punto):
    return pd.DataFrame(), None


def crear_nuevo_punto():
    st.session_state["punto_en_edicion"] = "Punto nuevo"


# =========================================================
# INTEGRACIÓN FINAL
# =========================================================

def cargar_entrada(**kwargs):
    return cargar_entrada(**kwargs)
