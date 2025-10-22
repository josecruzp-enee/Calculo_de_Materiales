# -*- coding: utf-8 -*-
"""
configuracion_cables.py
Versión completa restaurada con:
- Botones para configuraciones de red primaria y secundaria
- Ingreso de distancias (m)
- Cálculo automático del total de cable
- Guardado automático en st.session_state["datos_proyecto"]["cables_proyecto"]
"""

import streamlit as st
import pandas as pd


def seccion_cables():
    """Interfaz Streamlit para selección de configuración y cálculo de cables del proyecto."""

    st.markdown("## ⚙️ Configuración de Cables del Proyecto")
    st.markdown("Selecciona la configuración de red primaria y secundaria, calibres y distancias estimadas.")

    # === DATOS BASE ===
    datos_proyecto = st.session_state.get("datos_proyecto", {})
    cables_guardados = datos_proyecto.get("cables_proyecto", {})

    # === VALORES INICIALES ===
    tension = datos_proyecto.get("tension", 13.8)
    calibre_mt = cables_guardados.get("Calibre", "1/0 ACSR")
    calibre_bt = cables_guardados.get("Calibre_BT", "1/0 WP")
    calibre_neutro = cables_guardados.get("Calibre_Neutro", "#2 AWG")

    # === BLOQUE DE CONFIGURACIÓN PRIMARIA ===
    st.markdown("### ⚡ Configuración Primaria (MT)")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("1F + N", key="btn_mt_1f"):
            st.session_state["config_mt"] = "1F+N"
    with col2:
        if st.button("2F + N", key="btn_mt_2f"):
            st.session_state["config_mt"] = "2F+N"
    with col3:
        if st.button("3F + N", key="btn_mt_3f"):
            st.session_state["config_mt"] = "3F+N"

    config_mt = st.session_state.get("config_mt", "No seleccionada")
    st.info(f"🔹 Configuración primaria seleccionada: **{config_mt}**")

    # === BLOQUE DE CONFIGURACIÓN SECUNDARIA ===
    st.markdown("### 💡 Configuración Secundaria (BT)")
    col4, col5, col6, col7 = st.columns(4)
    with col4:
        if st.button("N", key="btn_bt_n"):
            st.session_state["config_bt"] = "N"
    with col5:
        if st.button("Hp + N", key="btn_bt_hp"):
            st.session_state["config_bt"] = "Hp+N"
    with col6:
        if st.button("2F + N", key="btn_bt_2f"):
            st.session_state["config_bt"] = "2F+N"
    with col7:
        if st.button("2F + Hp + N", key="btn_bt_2fhp"):
            st.session_state["config_bt"] = "2F+Hp+N"

    config_bt = st.session_state.get("config_bt", "No seleccionada")
    st.info(f"💡 Configuración secundaria seleccionada: **{config_bt}**")

    # === SELECCIÓN DE CALIBRES ===
    st.markdown("### 🧰 Calibres de Conductores")
    opciones_mt = ["1/0 ACSR", "3/0 ACSR", "266.8 MCM", "336.4 MCM"]
    opciones_bt = ["1/0 WP", "2/0 WP", "3/0 WP", "4/0 WP"]
    opciones_neutro = ["#2 AWG", "#4 AWG", "1/0 ACSR", "2/0 ACSR"]

    col8, col9, col10 = st.columns(3)
    with col8:
        calibre_mt_sel = st.selectbox("Calibre MT:", opciones_mt,
                                      index=opciones_mt.index(calibre_mt) if calibre_mt in opciones_mt else 0)
    with col9:
        calibre_bt_sel = st.selectbox("Calibre BT:", opciones_bt,
                                      index=opciones_bt.index(calibre_bt) if calibre_bt in opciones_bt else 0)
    with col10:
        calibre_neutro_sel = st.selectbox("Calibre Neutro:", opciones_neutro,
                                          index=opciones_neutro.index(calibre_neutro) if calibre_neutro in opciones_neutro else 0)

    # === DISTANCIAS ===
    st.markdown("### 📏 Distancias y Cálculo de Cable Total")
    col11, col12, col13 = st.columns(3)
    with col11:
        dist_mt = st.number_input("Distancia MT (m):", min_value=0.0, step=10.0, value=100.0)
    with col12:
        dist_bt = st.number_input("Distancia BT (m):", min_value=0.0, step=10.0, value=50.0)
    with col13:
        dist_neutro = st.number_input("Distancia Neutro (m):", min_value=0.0, step=10.0, value=50.0)

    # === CÁLCULO DE LONGITUD TOTAL (según configuración) ===
    def calcular_total(distancia, configuracion):
        """Devuelve longitud total considerando número de fases."""
        if "3F" in configuracion:
            return distancia * 3
        elif "2F" in configuracion:
            return distancia * 2
        elif "1F" in configuracion or "Hp" in configuracion:
            return distancia * 1
        else:
            return distancia

    total_mt = calcular_total(dist_mt, config_mt)
    total_bt = calcular_total(dist_bt, config_bt)
    total_neutro = dist_neutro  # Neutro siempre 1

    # === TABLA DE RESULTADOS ===
    df_cables = pd.DataFrame({
        "Tipo": ["Primario (MT)", "Secundario (BT)", "Neutro"],
        "Configuración": [config_mt, config_bt, "N"],
        "Calibre": [calibre_mt_sel, calibre_bt_sel, calibre_neutro_sel],
        "Longitud (m)": [dist_mt, dist_bt, dist_neutro],
        "Total Cable (m)": [total_mt, total_bt, total_neutro]
    })

    st.markdown("### 📘 Resumen de Cables Seleccionados")
    st.dataframe(df_cables, use_container_width=True, hide_index=True)

    # === GUARDAR EN SESSION_STATE ===
    datos_proyecto["tension"] = tension
    datos_proyecto["cables_proyecto"] = df_cables.to_dict("records")
    datos_proyecto["calibre_mt"] = calibre_mt_sel
    datos_proyecto["calibre_bt"] = calibre_bt_sel
    datos_proyecto["calibre_neutro"] = calibre_neutro_sel
    st.session_state["datos_proyecto"] = datos_proyecto

    st.success("✅ Configuración de cables guardada correctamente.")
    return df_cables.to_dict("records")
