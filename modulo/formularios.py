# -*- coding: utf-8 -*-
"""
formularios.py
Módulo de formularios para ingresar datos generales del proyecto.
Optimizado en diseño (dos columnas, menor espaciado).
Autor: José Nikol Cruz
"""

import streamlit as st
from datetime import date


def seccion_datos_proyecto():
    """Formulario compacto para ingresar los datos generales del proyecto."""
    st.markdown("### 📘 Datos Generales del Proyecto")

    # Crear dos columnas para reducir espacio vertical
    col1, col2 = st.columns(2)

    with col1:
        nombre_proyecto = st.text_input("📄 Nombre del Proyecto", key="nombre_proyecto")
        empresa = st.text_input("🏢 Empresa / Área", value="ENEE", key="empresa")
        nivel_tension = st.selectbox("⚡ Nivel de Tensión (kV)", ["13.8", "34.5"], key="nivel_tension")

    with col2:
        codigo_proyecto = st.text_input("🔢 Código / Expediente", key="codigo_proyecto")
        responsable = st.text_input("👷‍♂️ Responsable / Diseñador", key="responsable")
        fecha_informe = st.date_input("📅 Fecha del Informe", value=date.today(), key="fecha_informe")

    # Guardar los datos en el session_state
    datos = {
        "nombre_proyecto": nombre_proyecto,
        "codigo_proyecto": codigo_proyecto,
        "empresa": empresa,
        "responsable": responsable,
        "nivel_de_tension": nivel_tension,
        "fecha_informe": str(fecha_informe)
    }

    st.session_state["datos_proyecto"] = datos

    # Mostrar resumen visual
    st.markdown("#### 🧾 Resumen de Datos del Proyecto")
    st.write(datos)

    st.success("✅ Datos del proyecto guardados correctamente.")


def mostrar_datos_formateados():
    """Muestra los datos del proyecto en formato de tabla."""
    if "datos_proyecto" in st.session_state:
        datos = st.session_state["datos_proyecto"]
        st.markdown("#### 📄 Datos Guardados")
        for k, v in datos.items():
            st.write(f"**{k.replace('_', ' ').title()}**: {v}")
    else:
        st.warning("⚠️ Aún no se han ingresado datos del proyecto.")
