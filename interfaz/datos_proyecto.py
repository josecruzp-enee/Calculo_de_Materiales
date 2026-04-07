# -*- coding: utf-8 -*-
# interfaz/datos_proyecto.py

import streamlit as st
from interfaz.formularios import formulario_datos_proyecto, mostrar_datos_formateados


# =========================================================
# SECCIÓN DATOS DEL PROYECTO
# =========================================================

def seccion_datos_proyecto() -> dict:

    datos_nuevos = formulario_datos_proyecto()

    if datos_nuevos:
        st.session_state["datos_proyecto"] = datos_nuevos

    datos_actuales = st.session_state.get("datos_proyecto", {})

    # =========================================================
    # 🔥 CONVERSIÓN DE TENSIÓN (AQUÍ ESTÁ LA CLAVE)
    # =========================================================
    tension_str = datos_actuales.get("nivel_de_tension", "")

    if "/" in tension_str:
        try:
            _, t = tension_str.split("/")
            datos_actuales["tension"] = float(t)
        except:
            datos_actuales["tension"] = None
    else:
        try:
            datos_actuales["tension"] = float(tension_str)
        except:
            datos_actuales["tension"] = None

    st.session_state["datos_proyecto"] = datos_actuales

    # ============================
    mostrar_datos_formateados()

    return datos_actuales
