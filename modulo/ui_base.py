# modulo/ui_base.py
# -*- coding: utf-8 -*-
"""
Funciones base de UI: estado inicial, encabezado, selector de modo y reset de claves.
"""

import time
import pandas as pd
import streamlit as st
from modulo.estilos_app import aplicar_estilos

# Constante local usada para inicializar df_puntos
COLUMNAS_BASE = [
    "Punto", "Poste", "Primario", "Secundario",
    "Retenidas", "Conexiones a tierra", "Transformadores"
]

def inicializar_estado() -> None:
    """Inicializa claves esperadas en st.session_state sin sobrescribir valores existentes."""
    valores_por_defecto = {
        "datos_proyecto": {},
        "df_puntos": pd.DataFrame(columns=COLUMNAS_BASE),
        "materiales_extra": [],
        "calculo_finalizado": False,
        "punto_en_edicion": None,
        "cables_proyecto": {},
        "keys_desplegables": {},
        "pdfs_generados": None,
        "reiniciar_desplegables": False,
    }
    for clave, valor in valores_por_defecto.items():
        st.session_state.setdefault(clave, valor)

def renderizar_encabezado() -> None:
    """Configura la página y aplica estilos."""
    st.set_page_config(page_title="Cálculo de Materiales", layout="wide")
    aplicar_estilos()
    st.title("⚡ Cálculo de Materiales para Proyecto de Distribución")

def resetear_desplegables() -> None:
    """Fuerza nuevas keys para widgets de desplegables (evita estado pegado)."""
    claves = ["sel_poste", "sel_primario", "sel_secundario",
              "sel_retenidas", "sel_tierra", "sel_transformador"]
    for key in claves:
        st.session_state.pop(key, None)
    st.session_state["keys_desplegables"] = {k: f"{k}_{int(time.time()*1000)}" for k in claves}

def seleccionar_modo_carga() -> str:
    """Muestra el selector de modo de carga y retorna la opción elegida."""
    modo = st.radio(
        "Selecciona modo de carga:",
        ["Desde archivo Excel", "Pegar tabla", "Listas desplegables"],
        key="modo_carga_radio"
    )
    st.markdown("---")
    return modo

