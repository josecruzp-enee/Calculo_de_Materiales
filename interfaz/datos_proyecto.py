# -*- coding: utf-8 -*-
# interfaz/datos_proyecto.py

import streamlit as st
from interfaz.formularios import formulario_datos_proyecto, mostrar_datos_formateados


# =========================================================
# SECCIÓN DATOS DEL PROYECTO
# =========================================================

def seccion_datos_proyecto() -> dict:
    """
    Sección de datos del proyecto.

    ✔ Usa formulario (UI)
    ✔ Captura retorno (nuevo)
    ✔ Mantiene compatibilidad con session_state
    ✔ Retorna datos al orquestador
    """

    # ============================
    # FORMULARIO
    # ============================
    datos_nuevos = formulario_datos_proyecto()

    # ============================
    # ACTUALIZAR ESTADO (SI HAY NUEVOS DATOS)
    # ============================
    if datos_nuevos:
        st.session_state["datos_proyecto"] = datos_nuevos

    # ============================
    # OBTENER DATOS ACTUALES
    # ============================
    datos_actuales = st.session_state.get("datos_proyecto", {})

    # ============================
    # MOSTRAR DATOS
    # ============================
    mostrar_datos_formateados()

    # ============================
    # RETORNAR AL ORQUESTADOR
    # ============================
    return datos_actuales
