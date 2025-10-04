# -*- coding: utf-8 -*-
"""
Sección de configuración de cables del proyecto
Autor: José Nikol Cruz
"""

import streamlit as st
import pandas as pd

def seccion_cables():
    st.subheader("6. ⚡ Configuración de Cables del Proyecto")
    st.markdown("Define las longitudes y configuraciones de red por tipo de circuito (1F, 2F, 3F).")

    if "cables_proyecto" not in st.session_state:
        st.session_state["cables_proyecto"] = []

    FASES = {
        "Primario": {"1F": 1, "2F": 2, "3F": 3},
        "Secundario": {"1F": 1, "2F": 2},
        "Neutro": {"Única": 1},
        "Piloto": {"Única": 1},
    }

    tipos = list(FASES.keys())

    with st.form("form_cables"):
        col1, col2, col3, col4 = st.columns([1.3, 1.2, 1, 1.5])

        tipo = col1.selectbox("🔌 Tipo de circuito", tipos)
        configuraciones = list(FASES[tipo].keys())
        configuracion = col2.selectbox("⚙️ Configuración", configuraciones)

        # Cargar calibres desde el estado del proyecto
        datos_proyecto = st.session_state.get("datos_proyecto", {})
        calibres = {
            "Primario": datos_proyecto.get("calibre_primario", ""),
            "Secundario": datos_proyecto.get("calibre_secundario", ""),
            "Neutro": datos_proyecto.get("calibre_neutro", ""),
            "Piloto": datos_proyecto.get("calibre_piloto", "")
        }

        calibre = col3.text_input("📏 Calibre", calibres.get(tipo, ""), disabled=True)
        longitud = col4.number_input("📐 Longitud del tramo (m)", min_value=0.0, step=1.0)

        agregar = st.form_submit_button("➕ Agregar tramo")

    if agregar and tipo and configuracion and longitud > 0:
        fases = FASES[tipo][configuracion]
        total = longitud * fases
        st.session_state["cables_proyecto"].append({
            "Tipo": tipo,
            "Configuración": configuracion,
            "Calibre": calibres.get(tipo, ""),
            "Fases": fases,
            "Longitud": longitud,
            "Unidad": "m",
            "Total Cable": total
        })
        st.success(f"✅ {tipo} {configuracion} agregado ({total:.2f} m de cable)")

    if st.session_state["cables_proyecto"]:
        st.markdown("### 📋 Resumen de Cables")
        st.dataframe(pd.DataFrame(st.session_state["cables_proyecto"]), use_container_width=True)
