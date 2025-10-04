# -*- coding: utf-8 -*-
"""
Sección unificada: selección de calibres y configuración de cables
Autor: José Nikol Cruz
"""

import streamlit as st
import pandas as pd


def seccion_cables():
    """
    Sección combinada para definir calibres, configuraciones y longitudes de tramos.
    Guarda los datos en st.session_state["cables_proyecto"].
    """

    st.subheader("2️⃣ ⚡ Configuración y Calibres de Conductores")
    st.markdown("Define el tipo de circuito, configuración (1F, 2F, 3F), calibre y longitud total de los tramos.")

    # Inicializar lista de cables en sesión
    if "cables_proyecto" not in st.session_state:
        st.session_state["cables_proyecto"] = []

    # === Calibres por defecto ===
    calibres = {
        "Primario": ["2 ASCR", "1/0 ASCR", "2/0 ASCR", "3/0 ASCR", "4/0 ASCR", "266.8 MCM", "477 MCM", "556.5 MCM"],
        "Secundario": ["2 WP", "1/0 WP", "2/0 WP", "3/0 WP", "4/0 WP", "266.8 WP"],
        "Neutro": ["2 ASCR", "1/0 ASCR", "2/0 ASCR", "3/0 ASCR", "4/0 ASCR", "266.8 MCM"],
        "Piloto": ["2 WP", "4 WP", "6 WP"],
        "Retenidas": ["1/4 Acerado", "5/8 Acerado", "3/4 Acerado"]
    }

    # === Configuraciones posibles según tipo ===
    FASES = {
        "Primario": {"1F": 1, "2F": 2, "3F": 3},
        "Secundario": {"1F": 1, "2F": 2},
        "Neutro": {"Única": 1},
        "Piloto": {"Única": 1},
        "Retenidas": {"Única": 1},
    }

    tipos = list(FASES.keys())

    # === Formulario principal ===
    with st.form("form_cables_y_calibres"):
        col1, col2, col3, col4 = st.columns([1.5, 1.2, 1.5, 1.3])

        tipo = col1.selectbox("🔌 Tipo de circuito", tipos)
        configuraciones = list(FASES[tipo].keys())
        configuracion = col2.selectbox("⚙️ Configuración", configuraciones)

        calibre = col3.selectbox("📏 Calibre", calibres[tipo])
        longitud = col4.number_input("📐 Longitud del tramo (m)", min_value=0.0, step=1.0)

        agregar = st.form_submit_button("➕ Agregar tramo")

    # === Procesar tramo agregado ===
    if agregar and longitud > 0:
        fases = FASES[tipo][configuracion]
        total = longitud * fases
        st.session_state["cables_proyecto"].append({
            "Tipo": tipo,
            "Configuración": configuracion,
            "Calibre": calibre,
            "Fases": fases,
            "Longitud": longitud,
            "Unidad": "m",
            "Total Cable": total
        })
        st.success(f"✅ {tipo} {configuracion} agregado ({total:.2f} m de cable total)")

    # === Mostrar resumen de cables ===
    if st.session_state["cables_proyecto"]:
        st.markdown("### 📋 Resumen de Cables del Proyecto")
        df = pd.DataFrame(st.session_state["cables_proyecto"])
        st.dataframe(df, use_container_width=True, hide_index=True)

        # === Totales agrupados por tipo ===
        st.markdown("#### 🔢 Totales por tipo de conductor")
        df_totales = df.groupby("Tipo")["Total Cable"].sum().reset_index()
        df_totales.rename(columns={"Total Cable": "Total (m)"}, inplace=True)
        st.dataframe(df_totales, use_container_width=True, hide_index=True)

        # === Botones de gestión ===
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧹 Limpiar todos los tramos"):
                st.session_state["cables_proyecto"] = []
                st.success("✅ Se eliminaron todos los tramos registrados.")

        with col2:
            if st.button("💾 Confirmar selección"):
                st.session_state["datos_proyecto"]["cables_confirmados"] = True
                st.success("✅ Configuración de cables confirmada para el proyecto.")
