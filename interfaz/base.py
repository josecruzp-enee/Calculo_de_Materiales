# -*- coding: utf-8 -*-
# interfaz/base.py

import time
import os
import pandas as pd
import streamlit as st
from interfaz.estilos_app import aplicar_estilos


# ====== Constantes compartidas ======
COLUMNAS_BASE = [
    "Punto", "Poste", "Primario", "Secundario",
    "Retenidas", "Conexiones a tierra", "Transformadores", "Luminarias"
]

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # raíz del repo
RUTA_DATOS_MATERIALES_DEFECTO = os.path.join(BASE_DIR, "data", "Estructura_datos.xlsx")


# ====== Encabezado / estilos ======
def renderizar_encabezado() -> None:
    """Configura página y estilos, y dibuja encabezado fijo."""
    st.set_page_config(page_title="Cálculo de Materiales", layout="wide")
    aplicar_estilos()
    st.title("⚡ Cálculo de Materiales para Proyecto de Distribución")


# ====== Estado ======
def inicializar_estado() -> None:
    """Inicializa claves esperadas en st.session_state sin sobrescribir valores existentes."""
    valores_por_defecto = {
        "datos_proyecto": {},
        "df_puntos": pd.DataFrame(columns=COLUMNAS_BASE),
        "materiales_extra": [],
        "calculo_finalizado": False,
        "punto_en_edicion": None,
        "cables_proyecto": [],  # 🔥 CORREGIDO (antes estaba como dict)
        "keys_desplegables": {},
        "pdfs_generados": None,
        "reiniciar_desplegables": False,
    }
    for clave, valor in valores_por_defecto.items():
        st.session_state.setdefault(clave, valor)


def resetear_desplegables() -> None:
    """Fuerza nuevas keys para widgets de desplegables (evita estado pegado)."""
    claves = [
        "sel_poste",
        "sel_primario",
        "sel_secundario",
        "sel_retenidas",
        "sel_tierra",
        "sel_transformador",
    ]
    for key in claves:
        st.session_state.pop(key, None)

    st.session_state["keys_desplegables"] = {
        k: f"{k}_{int(time.time() * 1000)}" for k in claves
    }


# ====== Selector de modo ======

def seleccionar_modo_carga():

    st.markdown("### ⚙️ Modo de carga")

    opciones = {
        "dxf": "DXF (ENEE)",
        "excel": "Excel",
        "manual": "Manual"
    }

    keys = list(opciones.keys())

    # 🔥 asegurar estado válido
    modo_actual = st.session_state.get("modo_carga_seleccionado", "manual")

    if modo_actual not in keys:
        modo_actual = "manual"

    index_actual = keys.index(modo_actual)

    modo = st.radio(
        "Seleccione el tipo de entrada",
        keys,
        index=index_actual,
        format_func=lambda x: opciones[x],
        horizontal=True,
        key="radio_modo_carga"
    )

    # 🔥 persistencia
    st.session_state["modo_carga_seleccionado"] = modo
    st.session_state["tipo_entrada"] = modo



# ====== Ruta por defecto para materiales ======
def ruta_datos_materiales_por_defecto() -> str:
    return RUTA_DATOS_MATERIALES_DEFECTO
