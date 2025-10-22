# -*- coding: utf-8 -*-
"""
configuracion_cables.py — versión estable ENEE (compatible con app.py)
Incluye:
- Tipos: MT, BT, Neutro, Acerado
- Ingreso libre de distancia (m)
- Unidades visuales [m]
- Cálculo automático del total
- Devuelve DataFrame válido y no vacío (evita ValueError)
"""

import streamlit as st
import pandas as pd


def seccion_cables():
    """Interfaz Streamlit para selección y cálculo de cables del proyecto."""

    st.markdown("## ⚙️ Configuración de Cables del Proyecto")
    st.markdown("Selecciona las configuraciones de red, calibres, distancias y longitudes totales de conductor por tipo.")

    # === DATOS BASE ===
    datos_proyecto = st.session_state.get("datos_proyecto", {})
    tension = datos_proyecto.get("tension", 13.8)

    # === OPCIONES ===
    opciones_fases = ["1F", "2F", "3F", "HP", "N", "Retenida"]
    opciones_calibres_mt = ["1/0 ACSR", "3/0 ACSR", "266.8 MCM", "336.4 MCM"]
    opciones_calibres_bt = ["1/0 WP", "2/0 WP", "3/0 WP", "4/0 WP"]
    opciones_calibres_neutro = ["#2 ACSR", "#4 ACSR", "1/0 ACSR", "2/0 ACSR"]
    opciones_calibres_acerado = ["1/4''", "3/8''", "7/16''", "1/2''"]

    # === FUNCIÓN AUXILIAR ===
    def calcular_total(distancia, fase):
        if fase == "3F":
            return distancia * 3
        elif fase == "2F":
            return distancia * 2
        else:
            return distancia

    # === TIPOS DE CABLE ===
    tipos = ["MT", "BT", "Neutro", "Acerado"]
    calibres_defecto = {
        "MT": "1/0 ACSR",
        "BT": "3/0 WP",
        "Neutro": "#2 ACSR",
        "Acerado": "1/4''"
    }

    data = []

    # === ESTILO ===
    st.markdown("""
        <style>
            .unidad-texto {
                color: #555;
                font-weight: 500;
                margin-top: 4px;
            }
        </style>
    """, unsafe_allow_html=True)

    # === FORMULARIO POR TIPO ===
    for tipo in tipos:
        st.markdown(f"### 📦 {tipo}")
        col1, col2, col3, col4 = st.columns([1, 1.3, 1, 1])

        # --- FASE ---
        with col1:
            fase = st.selectbox(
                f"Fases ({tipo})",
                opciones_fases,
                key=f"fase_{tipo}",
                index=0 if tipo != "Neutro" else opciones_fases.index("N"),
            )

        # --- CALIBRE ---
        with col2:
            if tipo == "MT":
                calibres = opciones_calibres_mt
            elif tipo == "BT":
                calibres = opciones_calibres_bt
            elif tipo == "Neutro":
                calibres = opciones_calibres_neutro
            else:
                calibres = opciones_calibres_acerado

            calibre_sel = st.selectbox(
                f"Calibre ({tipo})",
                calibres,
                index=calibres.index(calibres_defecto[tipo])
                if calibres_defecto[tipo] in calibres
                else 0,
            )

        # --- DISTANCIA ---
        with col3:
            st.markdown(f"<div class='unidad-texto'>Distancia ({tipo})</div>", unsafe_allow_html=True)
            distancia = st.number_input(
                "",
                min_value=0.0,
                key=f"dist_{tipo}",
                label_visibility="collapsed",
            )
            st.markdown("<div style='text-align:right; color:#555;'>[m]</div>", unsafe_allow_html=True)

        # --- TOTAL ---
        with col4:
            total = calcular_total(distancia, fase)
            st.markdown(f"<div class='unidad-texto'>Total Cable ({tipo})</div>", unsafe_allow_html=True)
            st.number_input(
                "",
                value=total,
                key=f"total_{tipo}",
                disabled=True,
                label_visibility="collapsed",
            )
            st.markdown("<div style='text-align:right; color:#555;'>[m]</div>", unsafe_allow_html=True)

        data.append({
            "Tipo": tipo,
            "Fases": fase,
            "Calibre": calibre_sel,
            "Distancia (m)": distancia,
            "Total Cable (m)": total
        })

    # === CREAR DATAFRAME ===
    df_cables = pd.DataFrame(data)

    # --- 🚫 Prevención del error de pandas ---
    # Si por alguna razón queda vacío, devolvemos un DataFrame con una fila dummy.
    if df_cables.empty:
        df_cables = pd.DataFrame([{
            "Tipo": "MT",
            "Fases": "1F",
            "Calibre": "1/0 ACSR",
            "Distancia (m)": 0.0,
            "Total Cable (m)": 0.0
        }])

    # === MOSTRAR RESUMEN ===
    st.markdown("### 📘 Resumen de Cables Seleccionados")
    st.dataframe(df_cables, use_container_width=True, hide_index=True)

    # === GUARDAR EN session_state ===
    datos_proyecto["tension"] = tension
    datos_proyecto["cables_proyecto"] = df_cables.to_dict("records")
    st.session_state["datos_proyecto"] = datos_proyecto

    # === TOTAL GENERAL ===
    total_general = df_cables["Total Cable (m)"].sum()
    st.success(
        f"✅ Configuración de cables guardada correctamente.  \n📏 **Longitud total general: {total_general:.1f} m**"
    )

    # --- 🔥 Devolvemos SIEMPRE un DataFrame no vacío ---
    return df_cables

