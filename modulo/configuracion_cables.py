# -*- coding: utf-8 -*-
"""
configuracion_cables.py
Permite seleccionar los calibres de los conductores MT, BT, Neutro (N),
Retenidas y Piloto (HP), y los guarda en st.session_state['datos_proyecto'].
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
    """Interfaz Streamlit para ingresar la configuración de cables del proyecto."""
    st.markdown("### 2️⃣ ⚡ Configuración y Calibres de Conductores")

    # === Catálogos por tipo (renombrados a MT/BT/N/Retenida/HP) ===
    calibres_disponibles = {
        "MT": ["2 ASCR", "1/0 ASCR", "2/0 ASCR", "3/0 ASCR", "4/0 ASCR", "266.8 MCM", "336 MCM"],
        "BT": ["2 WP", "1/0 WP", "2/0 WP", "3/0 WP", "4/0 WP"],
        "N":  ["2 ASCR", "1/0 ASCR", "2/0 ASCR", "3/0 ASCR", "4/0 ASCR"],
        "Retenida": ["1/4 Acerado", "3/8 Acerado", "5/8 Acerado"],
        "HP": ["2 WP", "1/0 WP", "2/0 WP"],
    }

    configuraciones_disponibles = {
        "MT": ["1F", "2F", "3F"],
        "BT": ["1F", "2F"],
        "N":  ["Única"],      # neutro sin fases
        "Retenida": ["Única"],
        "HP": ["1F", "2F"],
    }

    # === Configuración base del proyecto ===
    datos_proyecto = st.session_state.get("datos_proyecto", {})

    # --- Calibres predeterminados globales (no dependen del tipo seleccionado) ---
    calibre_mt_actual = datos_proyecto.get("calibre_mt", "1/0 ACSR")
    calibre_bt_actual = datos_proyecto.get("calibre_bt", "1/0 WP")
    calibre_neutro_actual = datos_proyecto.get("calibre_neutro", "#2 AWG")

    opciones_mt = ["1/0 ACSR", "3/0 ACSR", "266.8 MCM", "336.4 MCM"]
    opciones_bt = ["1/0 WP", "2/0 WP", "3/0 WP", "4/0 WP"]
    opciones_neutro = ["#2 AWG", "#4 AWG", "1/0 ACSR", "2/0 ACSR"]

    # === Estilo para el selector horizontal tipo "tabla" ===
    st.markdown("""
    <style>
    .selector-box { border:1px solid #D0D7DE; border-radius:12px; padding:10px 12px; background:#ffffff; }
    div[role="radiogroup"] > div { gap:0.25rem !important; }
    div[role="radiogroup"] label {
        border:1px solid #D0D7DE; border-radius:10px; padding:6px 12px; margin:2px 4px;
        background:#F8FAFC; white-space:nowrap;
    }
    div[role="radiogroup"] input:checked + div p { font-weight:700 !important; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns([1.3, 1, 1.3, 1.2])

    with col1:
        # 🔁 Mantén compatibilidad con estados previos
        tipo_actual = st.session_state.get("tipo_tramo") or st.session_state.get("tipo") or "MT"
        if tipo_actual not in ["MT", "BT", "N", "HP", "Retenida"]:
            tipo_actual = "MT"

        st.markdown("**Tipo**")
        st.markdown('<div class="selector-box">', unsafe_allow_html=True)
        tipo = st.radio(
            label="",
            options=["MT", "BT", "N", "HP", "Retenida"],
            horizontal=True,
            index=["MT", "BT", "N", "HP", "Retenida"].index(tipo_actual),
            label_visibility="collapsed",
            key="tipo_tramo_radio",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # espejo de compatibilidad
        st.session_state["tipo_tramo"] = tipo
        st.session_state["tipo"] = tipo

        calibre_mt = st.selectbox(
            "⚡ Calibre del Primario (MT):",
            opciones_mt,
            index=opciones_mt.index(calibre_mt_actual) if calibre_mt_actual in opciones_mt else 0
        )

    with col2:
        cfg_options = configuraciones_disponibles[tipo]
        if cfg_options and cfg_options != ["Única"]:
            def_cfg = st.session_state.get("configuracion_cable", cfg_options[0])
            if def_cfg not in cfg_options:
                def_cfg = cfg_options[0]
            configuracion = st.selectbox("⚙️ Config.", cfg_options, index=cfg_options.index(def_cfg), key="configuracion_cable")
        else:
            configuracion = "Única"
            st.text_input("⚙️ Config.", value="Única", disabled=True, key="configuracion_no_aplica")

        calibre_bt = st.selectbox(
            "💡 Calibre del Secundario (BT):",
            opciones_bt,
            index=opciones_bt.index(calibre_bt_actual) if calibre_bt_actual in opciones_bt else 0
        )

    with col3:
        cal_list = calibres_disponibles[tipo]
        def_cal = st.session_state.get("calibre_cable", cal_list[0] if cal_list else "")
        if def_cal not in cal_list:
            def_cal = cal_list[0] if cal_list else ""
        calibre = st.selectbox("📏 Calibre", cal_list, index=cal_list.index(def_cal) if cal_list else 0, key="calibre_cable")

    with col4:
        longitud = st.number_input("📐 Longitud (m)", min_value=0.0, step=10.0, key="longitud_cable")

    # Derivar fases según configuración (1F, 2F, 3F, Única)
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


# =====================================================
# 2️⃣ FUNCIÓN PARA PDF
# =====================================================
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

    tabla = Table(data, colWidths=[1.2 * inch] * 5)
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

