# -*- coding: utf-8 -*-
"""
configuracion_cables.py
Versión estable original, restaurada fielmente.
Compatible 100 % con app.py y con toda la lógica posterior.
"""

import streamlit as st
import pandas as pd


def seccion_cables():
    """Configuración de Cables del Proyecto (versión estable original)."""

    st.markdown("## ⚙️ Configuración de Cables del Proyecto")
    st.markdown("Selecciona los tipos de conductor, fases, calibres y longitudes estimadas para el proyecto.")

    # === Datos base ===
    datos_proyecto = st.session_state.get("datos_proyecto", {})
    tension = datos_proyecto.get("tension", 13.8)

    # === Opciones generales ===
    opciones_fases = ["1F", "2F", "3F", "HP", "N", "Retenida"]
    opciones_calibres_mt = ["1/0 ACSR", "3/0 ACSR", "266.8 MCM", "336.4 MCM"]
    opciones_calibres_bt = ["1/0 WP", "2/0 WP", "3/0 WP", "4/0 WP"]
    opciones_calibres_neutro = ["#2 ACSR", "#4 ACSR", "1/0 ACSR", "2/0 ACSR"]
    opciones_calibres_piloto = ["#12 Cu", "#10 Cu", "#8 Cu"]
    opciones_calibres_retenida = ["1/4''", "3/8''", "7/16''", "1/2''"]

    # === Fases para cálculo del total ===
    n_fase = {"3F": 3, "2F": 2, "1F": 1, "HP": 1, "N": 1, "Retenida": 1}

    # === Tipos de cable ===
    tipos = ["MT", "BT", "Neutro", "Piloto", "Retenida"]
    calibres_defecto = {
        "MT": "1/0 ACSR",
        "BT": "3/0 WP",
        "Neutro": "#2 ACSR",
        "Piloto": "#12 Cu",
        "Retenida": "1/4''"
    }

    data = []

    # === Entradas por tipo ===
    for tipo in tipos:
        st.markdown(f"### 📦 {tipo}")
        col1, col2, col3, col4 = st.columns(4)

        # --- Fase ---
        with col1:
            fase = st.selectbox(f"Fases ({tipo})", opciones_fases, key=f"fase_{tipo}")

        # --- Calibre ---
        with col2:
            if tipo == "MT":
                opciones = opciones_calibres_mt
            elif tipo == "BT":
                opciones = opciones_calibres_bt
            elif tipo == "Neutro":
                opciones = opciones_calibres_neutro
            elif tipo == "Piloto":
                opciones = opciones_calibres_piloto
            else:
                opciones = opciones_calibres_retenida

            calibre = st.selectbox(
                f"Calibre ({tipo})",
                opciones,
                index=opciones.index(calibres_defecto[tipo]) if calibres_defecto[tipo] in opciones else 0,
                key=f"calibre_{tipo}"
            )

        # --- Distancia ---
        with col3:
            distancia = st.number_input(f"Distancia ({tipo}) (m)", min_value=0.0, key=f"dist_{tipo}")

        # --- Total ---
        with col4:
            total = distancia * n_fase.get(fase, 1)
            st.number_input(f"Total Cable ({tipo}) (m)", value=total, key=f"total_{tipo}", disabled=True)

        data.append({
            "Tipo": tipo,
            "Fases": fase,
            "Calibre": calibre,
            "Distancia (m)": distancia,
            "Total Cable (m)": total
        })

    # === Crear DataFrame y mostrar resumen ===
    df = pd.DataFrame(data)

    st.markdown("### 📘 Resumen de Cables Seleccionados")
    st.dataframe(df, use_container_width=True)

    total_general = df["Total Cable (m)"].sum()
    st.success(f"✅ Configuración de cables guardada correctamente. Total general: {total_general:.1f} m")

    # === Guardar en session_state ===
    datos_proyecto["tension"] = tension
    datos_proyecto["cables_proyecto"] = df.to_dict("records")
    st.session_state["datos_proyecto"] = datos_proyecto

    return df
