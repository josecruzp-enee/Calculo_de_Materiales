# -*- coding: utf-8 -*-
"""
formulario.py
Gestión de formulario de datos del proyecto y selección de calibres
"""

import streamlit as st
from modulo.calibres import seleccionar_calibres_formulario


def formulario_datos_proyecto():
    """Formulario para ingresar los datos generales del proyecto"""
    st.markdown("## 1. 📋 Datos del Proyecto")

    datos = {
        "nombre": st.text_input("Nombre del proyecto", ""),
        "ubicacion": st.text_input("Ubicación", ""),
        "tension": st.selectbox("Nivel de Tensión (kV)", ["13.8", "34.5", "4.16"]),
        "ingeniero": st.text_input("Ingeniero responsable", ""),
    }

    # ---------------- SECCIÓN 2: CALIBRES ----------------
    st.markdown("### 2. 🧵 Selección de Calibres")

    # ⚙️ Calibres definidos internamente (sin Excel)
    calibres = {
        "primario": ["2 ASCR", "1/0 ASCR", "2/0 ASCR", "3/0 ASCR", "4/0 ACSR", "266.8 MCM", "477 MCM", "556.5 MCM"],
        "secundario": ["2 WP", "1/0 WP", "2/0 WP", "3/0 WP", "4/0 WP", "266.8 WP"],
        "neutro": ["2 ASCR", "1/0 ASCR", "2/0 ASCR", "3/0 ASCR", "4/0 ACSR", "266.8 MCM"],
        "piloto": ["2 WP"],
        "retenidas": ["1/4 Acerado", "5/8 Acerado", "3/4 Acerado"]
    }

    calibres_seleccionados = seleccionar_calibres_formulario(datos, calibres)

    # Guardar todo en session_state
    st.session_state["datos_proyecto"] = {
        **datos,
        **calibres_seleccionados
    }

    st.success("✅ Datos del proyecto guardados correctamente.")


def mostrar_datos_formateados():
    """Muestra los datos cargados del proyecto en forma de tabla."""
    if "datos_proyecto" in st.session_state:
        st.subheader("📊 Resumen de Datos del Proyecto")
        datos = st.session_state["datos_proyecto"]
        for clave, valor in datos.items():
            st.markdown(f"**{clave.capitalize()}:** {valor}")
