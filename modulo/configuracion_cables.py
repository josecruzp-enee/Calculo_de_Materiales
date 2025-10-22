# -*- coding: utf-8 -*-
"""
configuracion_cables.py — versión tipo tabla
Versión estable y funcional que muestra todos los tipos de cable en una misma tabla.
Compatible con app.py sin ValueError.
"""

import streamlit as st
import pandas as pd


def seccion_cables():
    """Configuración de Cables del Proyecto en formato tabular."""

    st.markdown("## ⚙️ Configuración de Cables del Proyecto")
    st.markdown(
        "Define los tipos de conductor, cantidad de fases, calibre y longitud estimada para cada circuito."
    )

    # === Catálogos ===
    opciones_fases = ["1F", "2F", "3F", "HP", "N", "Retenida"]
    opciones_mt = ["1/0 ACSR", "3/0 ACSR", "266.8 MCM", "336.4 MCM"]
    opciones_bt = ["1/0 WP", "2/0 WP", "3/0 WP", "4/0 WP"]
    opciones_neutro = ["#2 ACSR", "#4 ACSR", "1/0 ACSR", "2/0 ACSR"]
    opciones_piloto = ["#12 Cu", "#10 Cu", "#8 Cu"]
    opciones_retenida = ["1/4''", "3/8''", "7/16''", "1/2''"]

    # === Nº de fases por tipo ===
    n_fase = {"3F": 3, "2F": 2, "1F": 1, "HP": 1, "N": 1, "Retenida": 1}

    # === Tabla base ===
    tipos = ["MT", "BT", "Neutro", "Piloto", "Retenida"]
    calibres_defecto = {
        "MT": "1/0 ACSR",
        "BT": "3/0 WP",
        "Neutro": "#2 ACSR",
        "Piloto": "#12 Cu",
        "Retenida": "1/4''",
    }

    st.markdown("---")
    st.markdown("### 📋 Tabla General de Conductores")

    data = []
    for tipo in tipos:
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1.5, 1, 1])
        with col1:
            fase = st.selectbox(f"Fases ({tipo})", opciones_fases, key=f"fase_{tipo}")
        with col2:
            if tipo == "MT":
                opciones = opciones_mt
            elif tipo == "BT":
                opciones = opciones_bt
            elif tipo == "Neutro":
                opciones = opciones_neutro
            elif tipo == "Piloto":
                opciones = opciones_piloto
            else:
                opciones = opciones_retenida
            calibre = st.selectbox(
                f"Calibre ({tipo})", opciones, index=opciones.index(calibres_defecto[tipo])
            )
        with col3:
            distancia = st.number_input(f"Distancia ({tipo}) [m]", min_value=0.0, key=f"dist_{tipo}")
        with col4:
            total = distancia * n_fase.get(fase, 1)
            st.number_input(
                f"Total Cable ({tipo}) [m]",
                value=total,
                key=f"total_{tipo}",
                disabled=True,
            )
        with col5:
            st.text_input("Unidad", "m", key=f"unidad_{tipo}", disabled=True)

        data.append(
            {
                "Tipo": tipo,
                "Fases": fase,
                "Calibre": calibre,
                "Distancia (m)": distancia,
                "Total Cable (m)": total,
            }
        )

    df = pd.DataFrame(data)

    st.markdown("### 📘 Resumen de Cables Seleccionados")
    st.dataframe(df, use_container_width=True, hide_index=True)

    total_general = df["Total Cable (m)"].sum()
    st.success(f"✅ Configuración guardada. 📏 **Longitud total general: {total_general:.1f} m**")

    # === Guardar en session_state ===
    datos_proyecto = st.session_state.get("datos_proyecto", {})
    datos_proyecto["cables_proyecto"] = df.to_dict("records")
    st.session_state["datos_proyecto"] = datos_proyecto

    return df
