# -*- coding: utf-8 -*-
"""
formularios.py
Módulo de formularios para ingresar datos generales del proyecto.
Optimizado en diseño (dos columnas, menor espaciado).
Autor: José Nikol Cruz
"""

import streamlit as st
from datetime import date


def formulario_datos_proyecto():
    """Formulario compacto para ingresar los datos generales del proyecto (sin bloque de resumen)."""
    st.markdown("### 📘 Datos Generales del Proyecto")

    # Dos columnas para menor altura
    col1, col2 = st.columns(2)

    with col1:
        nombre_proyecto = st.text_input("📄 Nombre del Proyecto", key="nombre_proyecto")
        empresa = st.text_input("🏢 Empresa / Área", value="ENEE", key="empresa")
        nivel_tension = st.selectbox("⚡ Nivel de Tensión (kV)", ["13.8", "34.5"], key="nivel_tension")

    with col2:
        codigo_proyecto = st.text_input("🔢 Código / Expediente", key="codigo_proyecto")
        responsable = st.text_input("👷‍♂️ Responsable / Diseñador", key="responsable")
        fecha_informe = st.date_input("📅 Fecha del Informe", value=date.today(), key="fecha_informe")

    # Persistir en session_state (sin mostrar JSON)
    st.session_state["datos_proyecto"] = {
        "nombre_proyecto": nombre_proyecto,
        "codigo_proyecto": codigo_proyecto,
        "empresa": empresa,
        "responsable": responsable,
        "nivel_de_tension": nivel_tension,
        "fecha_informe": str(fecha_informe),
    }

    # Aviso breve de guardado
    st.success("✅ Datos del proyecto guardados correctamente.")


def mostrar_datos_formateados(show=False):
    """
    (Opcional) Muestra un bloque compacto de 'Datos Guardados'.
    Por defecto NO muestra nada para mantener la interfaz limpia.
    """
    if not show:
        return

    datos = st.session_state.get("datos_proyecto") or {}
    if not datos:
        st.warning("⚠️ Aún no se han ingresado datos del proyecto.")
        return

    st.markdown("#### 📄 Datos Guardados")
    st.write(f"**Nombre Proyecto:** {datos.get('nombre_proyecto','')}")
    st.write(f"**Código Proyecto:** {datos.get('codigo_proyecto','')}")
    st.write(f"**Empresa:** {datos.get('empresa','')}")
    st.write(f"**Responsable:** {datos.get('responsable','')}")
    st.write(f"**Nivel de Tensión:** {datos.get('nivel_de_tension','')}")
    st.write(f"**Fecha del Informe:** {datos.get('fecha_informe','')}")

