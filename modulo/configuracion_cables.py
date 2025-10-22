# -*- coding: utf-8 -*-
"""
configuracion_cables.py
Permite seleccionar los calibres de los conductores Primario (MT), Secundario (BT) y Neutro
y los guarda en st.session_state['datos_proyecto'].
"""

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
        "Retenidas": ["1/4 Acerado", "3/8 Acerado", "5/8 Acerado"],
        "Piloto": ["2 WP", "1/0 WP", "2/0 WP"],
    }

    # === Configuraciones disponibles ===
    configuraciones_disponibles = {
        "Primario": ["1F", "2F", "3F"],
        "Secundario": ["1F", "2F"],
        "Neutro": ["1F"],        # ⚡ Neutro monofásico fijo
        "Retenidas": ["Única"],
        "Piloto": ["1F", "2F"],  # ⚡ Piloto permite 120/240 V
    }

    # === Campos de entrada ===
    col1, col2, col3, col4 = st.columns([1.3, 1, 1.3, 1.2])
    """Interfaz Streamlit para seleccionar calibres de los cables del proyecto."""

    st.markdown("### ⚡ Configuración de Cables del Proyecto")
    st.markdown("Selecciona los calibres de conductor utilizados en la red primaria, secundaria y neutro.")

    # --- Valores actuales o predeterminados ---
    datos_proyecto = st.session_state.get("datos_proyecto", {})

    calibre_mt_actual = datos_proyecto.get("calibre_mt", "1/0 ACSR")
    calibre_bt_actual = datos_proyecto.get("calibre_bt", "1/0 WP")
    calibre_neutro_actual = datos_proyecto.get("calibre_neutro", "#2 AWG")

    # --- Opciones típicas de calibres ---
    opciones_mt = ["1/0 ACSR", "3/0 ACSR", "266.8 MCM", "336.4 MCM"]
    opciones_bt = ["1/0 WP", "2/0 WP", "3/0 WP", "4/0 WP"]
    opciones_neutro = ["#2 AWG", "#4 AWG", "1/0 ACSR", "2/0 ACSR"]

    # --- Diseño visual ---
    col1, col2, col3 = st.columns(3)

    with col1:
        tipo = st.selectbox(
            "🔌 Tipo",
            options=list(calibres_disponibles.keys()),
            index=0,
            key="tipo_circuito"
        calibre_mt = st.selectbox(
            "⚡ Calibre del Primario (MT):",
            opciones_mt,
            index=opciones_mt.index(calibre_mt_actual) if calibre_mt_actual in opciones_mt else 0
        )

    # --- Configuración según tipo ---
    with col2:
        if tipo == "Neutro":
            # 👇 Mantiene el mismo diseño pero bloquea la edición
            configuracion = st.text_input("⚙️ Config.", value="1F", disabled=True, key="configuracion_neutro")
        else:
            configuracion = st.selectbox("⚙️ Config.", configuraciones_disponibles[tipo], key="configuracion_cable")
        calibre_bt = st.selectbox(
            "💡 Calibre del Secundario (BT):",
            opciones_bt,
            index=opciones_bt.index(calibre_bt_actual) if calibre_bt_actual in opciones_bt else 0
        )

    with col3:
        calibre = st.selectbox("📏 Calibre", calibres_disponibles[tipo], key="calibre_cable")

    with col4:
        longitud = st.number_input("📐 Longitud (m)", min_value=0.0, step=10.0, key="longitud_cable")

    # Derivar fases según configuración (1F, 2F, 3F)
    fases = 1 if configuracion == "Única" else int(str(configuracion).replace("F", ""))
    total_cable = longitud * fases

    # Inicializar lista
    if "cables_proyecto" not in st.session_state:
        st.session_state.cables_proyecto = []

    # --- Botón agregar tramo ---
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

    # --- Mostrar tabla resultante ---
    if st.session_state.cables_proyecto:
        df = pd.DataFrame(st.session_state.cables_proyecto)
        st.dataframe(df, use_container_width=True)
        total = df["Total Cable (m)"].sum()
        st.markdown(f"**🧮 Total Global de Cable:** {total:.2f} m")

    return st.session_state.get("cables_proyecto", [])

def tabla_cables_pdf(datos_proyecto):
    """Genera tabla de configuración y calibres de cables para insertar en el PDF."""
    elems = []
    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    styleH = styles["Heading2"]

    if "cables_proyecto" not in datos_proyecto or not datos_proyecto["cables_proyecto"]:
        return elems  # No hay datos → no agregar nada

    elems.append(Spacer(1, 0.2 * inch))
    elems.append(Paragraph("⚡ Configuración y Calibres de Conductores", styleH))
    elems.append(Spacer(1, 0.1 * inch))

    df = pd.DataFrame(datos_proyecto["cables_proyecto"])

    data = [["Tipo", "Configuración", "Calibre", "Longitud (m)", "Total Cable (m)"]]
    for _, row in df.iterrows():
        data.append([
            str(row["Tipo"]),
            str(row["Configuración"]),
            str(row["Calibre"]),
            f"{row['Longitud (m)']:.2f}",
            f"{row['Total Cable (m)']:.2f}",
        ])

    tabla = Table(data, colWidths=[1.2 * inch] * 6)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))

    elems.append(tabla)
    elems.append(Spacer(1, 0.15 * inch))

    total = df["Total Cable (m)"].sum()
    elems.append(Paragraph(f"🧮 <b>Total Global de Cable:</b> {total:,.2f} m", styleN))
    elems.append(Spacer(1, 0.25 * inch))
    return elems
        calibre_neutro = st.selectbox(
            "🔩 Calibre del Neutro:",
            opciones_neutro,
            index=opciones_neutro.index(calibre_neutro_actual) if calibre_neutro_actual in opciones_neutro else 0
        )

    # --- Guardar automáticamente en session_state ---
    datos_proyecto["calibre_mt"] = calibre_mt
    datos_proyecto["calibre_bt"] = calibre_bt
    datos_proyecto["calibre_neutro"] = calibre_neutro

    st.session_state["datos_proyecto"] = datos_proyecto

    # --- Mostrar resumen ---
    st.markdown("#### 📘 Resumen de Calibres Seleccionados")
    st.write(pd.DataFrame({
        "Tipo de Conductor": ["Primario (MT)", "Secundario (BT)", "Neutro"],
        "Calibre Seleccionado": [calibre_mt, calibre_bt, calibre_neutro]
    }))

    st.success("✅ Los calibres han sido guardados correctamente en los datos del proyecto.")

