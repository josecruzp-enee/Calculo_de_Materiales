# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

# =====================================================
# 1️⃣ SECCIÓN STREAMLIT: CONFIGURACIÓN DE CABLES
# =====================================================
def seccion_cables():
    """Permite ingresar la configuración de cables del proyecto en Streamlit."""
    st.markdown("### 2️⃣ ⚡ Configuración y Calibres de Conductores")

    # === Listas de calibres por tipo ===
    calibres_disponibles = {
        "Primario": ["2 ASCR", "1/0 ASCR", "2/0 ASCR", "3/0 ASCR", "4/0 ASCR", "266.8 MCM", "336 MCM"],
        "Secundario": ["2 WP", "1/0 WP", "2/0 WP", "3/0 WP", "4/0 WP"],
        "Neutro": ["2 ASCR", "1/0 ASCR", "2/0 ASCR", "3/0 ASCR", "4/0 ASCR"],
        "Retenidas": ["1/4 Acerado", "3/8 Acerado", "5/8 Acerado"]
    }

    configuraciones_disponibles = {
        "Primario": ["1F", "2F", "3F"],
        "Secundario": ["1F", "2F"],
        "Neutro": ["Única"],
        "Retenidas": ["Única"]
    }

    # === Campos en una fila ===
    col1, col2, col3, col4 = st.columns([1.3, 1, 1.3, 1.2])

    with col1:
        tipo = st.selectbox("🔌 Tipo", list(calibres_disponibles.keys()), key="tipo_circuito")
    with col2:
        configuracion = st.selectbox("⚙️ Config.", configuraciones_disponibles[tipo], key="configuracion_cable")
    with col3:
        calibre = st.selectbox("📏 Calibre", calibres_disponibles[tipo], key="calibre_cable")
    with col4:
        longitud = st.number_input("📐 Longitud (m)", min_value=0.0, step=10.0, key="longitud_cable")

    # Derivar fases según configuración (solo aplica si no es "Única")
    if configuracion == "Única":
        fases = 1
    else:
        fases = int(configuracion.replace("F", ""))

    total_cable = longitud * fases

    # Inicializar lista si no existe
    if "cables_proyecto" not in st.session_state:
        st.session_state.cables_proyecto = []

    # Botón agregar tramo
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("➕ Agregar tramo"):
        st.session_state.cables_proyecto.append({
            "Tipo": tipo,
            "Configuración": configuracion,
            "Calibre": calibre,
            "Longitud (m)": longitud,
            "Total Cable (m)": total_cable
        })
        st.success(f"✅ {tipo} agregado ({total_cable:.2f} m totales).")

    # Mostrar tabla con totales
    if st.session_state.cables_proyecto:
        df = pd.DataFrame(st.session_state.cables_proyecto)
        st.dataframe(df, use_container_width=True)
        total = df["Total Cable (m)"].sum()
        st.markdown(f"**🧮 Total Global de Cable:** {total:.2f} m")

    return st.session_state.get("cables_proyecto", [])

