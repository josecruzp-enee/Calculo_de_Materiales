# -*- coding: utf-8 -*-
"""
configuracion_cables.py
Permite seleccionar los calibres de los conductores Primario (MT), Secundario (BT) y Neutro
y los guarda en st.session_state['datos_proyecto'].
"""

import streamlit as st
import pandas as pd


def seccion_cables():
    """Interfaz Streamlit para seleccionar calibres de los cables del proyecto."""

    st.markdown("### ⚡ Configuración de Cables del Proyecto")
    st.markdown("Selecciona los calibres de conductor utilizados en la red primaria, secundaria y neutro.")

    # --- Valores actuales o predeterminados ---
    datos_proyecto = st.session_state.get("datos_proyecto", {})

    calibre_mt_actual = datos_proyecto.get("calibre_mt", "1/0 ACSR")
    calibre_bt_actual = datos_proyecto.get("calibre_bt", "1/0 WP")
    calibre_neutro_actual = datos_proyecto.get("calibre_neutro", "#2 AWG")

    # --- Opciones típicas de calibres ---
    opciones_mt = ["1/0 ACSR", "3/0 ACSR", "266.8 MCM", "336.4 MCM"]
    opciones_bt = ["1/0 WP", "2/0 WP", "3/0 WP", "4/0 WP"]
    opciones_neutro = ["#2 AWG", "#4 AWG", "1/0 ACSR", "2/0 ACSR"]

    # --- Diseño visual ---
    col1, col2, col3 = st.columns(3)

    with col1:
        calibre_mt = st.selectbox(
            "⚡ Calibre del Primario (MT):",
            opciones_mt,
            index=opciones_mt.index(calibre_mt_actual) if calibre_mt_actual in opciones_mt else 0
        )

    with col2:
        calibre_bt = st.selectbox(
            "💡 Calibre del Secundario (BT):",
            opciones_bt,
            index=opciones_bt.index(calibre_bt_actual) if calibre_bt_actual in opciones_bt else 0
        )

    with col3:
        calibre_neutro = st.selectbox(
            "🔩 Calibre del Neutro:",
            opciones_neutro,
            index=opciones_neutro.index(calibre_neutro_actual) if calibre_neutro_actual in opciones_neutro else 0
        )

    # --- Guardar automáticamente en session_state ---
    datos_proyecto["calibre_mt"] = calibre_mt
    datos_proyecto["calibre_bt"] = calibre_bt
    datos_proyecto["calibre_neutro"] = calibre_neutro

    st.session_state["datos_proyecto"] = datos_proyecto

    # --- Mostrar resumen ---
    st.markdown("#### 📘 Resumen de Calibres Seleccionados")
    st.write(pd.DataFrame({
        "Tipo de Conductor": ["Primario (MT)", "Secundario (BT)", "Neutro"],
        "Calibre Seleccionado": [calibre_mt, calibre_bt, calibre_neutro]
    }))

    st.success("✅ Los calibres han sido guardados correctamente en los datos del proyecto.")

