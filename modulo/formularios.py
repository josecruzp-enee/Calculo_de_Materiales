# -*- coding: utf-8 -*-
"""
Formulario principal del proyecto.
Autor: José Nikol Cruz
"""

import streamlit as st
from datetime import datetime
from modulo.calibres import seleccionar_calibres_formulario


def formulario_datos_proyecto():
    """Formulario para ingresar los datos generales del proyecto."""
    st.markdown("### 1️⃣ Datos Generales del Proyecto")

    # --- Campos básicos ---
    nombre = st.text_input("📘 Nombre del Proyecto", value=st.session_state.get("nombre_proyecto", ""))
    codigo = st.text_input("🔢 Código / Expediente", value=st.session_state.get("codigo_proyecto", ""))
    empresa = st.text_input("🏢 Empresa / Área", value=st.session_state.get("empresa", "ENEE"))
    responsable = st.text_input("👷‍♂️ Responsable / Diseñador", value=st.session_state.get("responsable", ""))
    nivel_tension = st.selectbox("⚡ Nivel de Tensión (kV)", ["13.8", "34.5"], index=0)

    # --- Sección 2: Calibres (sin Excel) ---
    st.markdown("### 2️⃣ Selección de Calibres de Conductores")

    calibres_seleccionados = seleccionar_calibres_formulario(
        st.session_state.get("datos_proyecto", {})
    )

    # --- Guardar datos ---
    st.session_state["datos_proyecto"] = {
        "nombre_proyecto": nombre,
        "codigo_proyecto": codigo,
        "empresa": empresa,
        "responsable": responsable,
        "nivel_de_tension": nivel_tension,
        **calibres_seleccionados,
        "fecha_informe": datetime.today().strftime("%d/%m/%Y")
    }


def mostrar_datos_formateados():
    """Muestra los datos ingresados de forma ordenada."""
    if "datos_proyecto" in st.session_state:
        st.markdown("### 🧾 Resumen de Datos del Proyecto")
        datos = st.session_state["datos_proyecto"]
        st.json(datos)
