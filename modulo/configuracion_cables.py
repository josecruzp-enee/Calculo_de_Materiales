# -*- coding: utf-8 -*-
"""
configuracion_cables.py
Versión estable original
- Compatible 100% con app.py
- Sin modificaciones de estilo ni comportamiento
"""

import streamlit as st
import pandas as pd


def seccion_cables():
    """Interfaz Streamlit para selección de configuración y cálculo de cables del proyecto."""

    st.markdown("## ⚙️ Configuración de Cables del Proyecto")
    st.markdown("Selecciona la configuración de red primaria y secundaria, calibres y distancias estimadas.")

    datos_proyecto = st.session_state.get("datos_proyecto", {})
    tension = datos_proyecto.get("tension", 13.8)

    opciones_fases = ["1F", "2F", "3F", "HP", "N", "Retenida"]
    opciones_calibres_mt = ["1/0 ACSR", "3/0 ACSR", "266.8 MCM", "336.4 MCM"]
    opciones_calibres_bt = ["1/0 WP", "2/0 WP", "3/0 WP", "4/0 WP"]
    opciones_calibres_neutro = ["#2 ACSR", "#4 ACSR", "1/0 ACSR", "2/0 ACSR"]
    opciones_calibres_acerado = ["1/4''", "3/8''", "7/16''", "1/2''"]

    def calcular_total(distancia, fase):
        if "3F" in fase:
            return distancia * 3
        elif "2F" in fase:
            return distancia * 2
        else:
            return distancia

    tipos = ["MT", "BT", "Neutro", "Acerado"]
    calibres_defecto = {
        "MT": "1/0 ACSR",
        "BT": "3/0 WP",
        "Neutro": "#2 ACSR",
        "Acerado": "1/4''"
    }

    data = []
    for tipo in tipos:
        st.markdown(f"### 📦 {tipo}")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            fase = st.selectbox(f"Fases ({tipo})", opciones_fases, key=f"fase_{tipo}",
                                index=0 if tipo != "Neutro" else opciones_fases.index("N"))
        with col2:
            if tipo == "MT":
                calibres = opciones_calibres_mt
            elif tipo == "BT":
                calibres = opciones_calibres_bt
            elif tipo == "Neutro":
                calibres = opciones_calibres_neutro
            else:
                calibres = opciones_calibres_acerado
            calibre = st.selectbox(f"Calibre ({tipo})", calibres,
                                   index=calibres.index(calibres_defecto[tipo]))
        with col3:
            distancia = st.number_input(f"Distancia ({tipo}) (m)", min_value=0.0, key=f"dist_{tipo}")
        with col4:
            total = calcular_total(distancia, fase)
            st.number_input(f"Total Cable ({tipo}) (m)", value=total, disabled=True, key=f"tot_{tipo}")

        data.append({
            "Tipo": tipo,
            "Fases": fase,
            "Calibre": calibre,
            "Distancia (m)": distancia,
            "Total Cable (m)": total
        })

    df = pd.DataFrame(data)
    st.markdown("### 📘 Resumen de Cables Seleccionados")
    st.dataframe(df, use_container_width=True)

    total_general = df["Total Cable (m)"].sum()
    st.success(f"✅ Configuración guardada correctamente. Total general: {total_general:.1f} m")

    datos_proyecto["tension"] = tension
    datos_proyecto["cables_proyecto"] = df.to_dict("records")
    st.session_state["datos_proyecto"] = datos_proyecto

    return df
