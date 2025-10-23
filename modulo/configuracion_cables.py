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


def seccion_cables():
    """Interfaz Streamlit como TABLA editable para configurar tramos de cable."""
    st.markdown("### 2️⃣ ⚡ Configuración y calibres de conductores (tabla)")

    # ----- Catálogos -----
    CALIBRES = {
        "MT": ["2 ASCR", "1/0 ASCR", "2/0 ASCR", "3/0 ASCR", "4/0 ASCR", "266.8 MCM", "336 MCM"],
        "BT": ["2 WP", "1/0 WP", "2/0 WP", "3/0 WP", "4/0 WP"],
        "N":  ["2 ASCR", "1/0 ASCR", "2/0 ASCR", "3/0 ASCR", "4/0 ASCR"],
        "HP": ["2 WP", "1/0 WP", "2/0 WP"],
        "Retenida": ["1/4", "5/8", "3/4"],   # <- como pediste
    }
    TIPOS = ["MT", "BT", "N", "HP", "Retenida"]

    CONFIGS_BY_TIPO = {
        "MT": ["1F", "2F", "3F"],
        "BT": ["1F", "2F", "3F"],
        "N":  ["N"],
        "HP": ["1F+N", "2F"],
        "Retenida": ["Única"],               # retenida no lleva fases
    }

    # Unión ordenada de todas las configuraciones para el editor
    CONFIGS_UNION = ["Única", "N", "1F", "1F+N", "2F", "3F"]

    # Unión de todos los calibres (el post-proceso restringe por tipo)
    CALIBRES_UNION = list(dict.fromkeys(c for lst in CALIBRES.values() for c in lst))

    # ---- Estado inicial
    if "cables_proyecto_df" not in st.session_state:
        st.session_state["cables_proyecto_df"] = pd.DataFrame(
            columns=["Tipo", "Configuración", "Calibre", "Longitud (m)", "Total Cable (m)"]
        )

    st.caption("Agrega/edita filas; el total se calcula automáticamente según la configuración.")

    # --- Editor de tabla
    edited_df = st.data_editor(
        st.session_state["cables_proyecto_df"],
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Tipo": st.column_config.SelectboxColumn(
                "Tipo", options=TIPOS, required=True, width="small",
                help="MT, BT, N (neutro), HP (piloto), Retenida",
            ),
            "Configuración": st.column_config.SelectboxColumn(
                "Config.", options=CONFIGS_UNION, required=True, width="small",
                help="MT/BT: 1F,2F,3F · N: N · HP: 1F+N/2F · Retenida: Única",
            ),
            "Calibre": st.column_config.SelectboxColumn(
                "Calibre", options=CALIBRES_UNION, required=True, width="medium",
            ),
            "Longitud (m)": st.column_config.NumberColumn(
                "Longitud (m)", min_value=0.0, step=10.0, format="%.2f",
            ),
            "Total Cable (m)": st.column_config.NumberColumn(
                "Total Cable (m)", disabled=True, format="%.2f",
                help="Longitud × Nº de conductores/fases (autocalculado)",
            ),
        },
        hide_index=True,
    )

    # --- Reglas de negocio + cálculo de total por fila ---
    def fases_de(cfg: str) -> int:
        if not isinstance(cfg, str):
            return 1
        cfg = cfg.strip()
        if cfg in ("Única", "N", "1F", "1F+N"):
            return 1
        if cfg == "2F":
            return 2
        if cfg == "3F":
            return 3
        return 1

    processed = []
    for _, row in edited_df.fillna("").iterrows():
        if not row.get("Tipo"):
            continue
        tipo = str(row["Tipo"])

        # Ajustar configuración permitida por tipo
        cfg_permitidas = CONFIGS_BY_TIPO.get(tipo, ["Única"])
        cfg = str(row["Configuración"]) if row.get("Configuración") else cfg_permitidas[0]
        if cfg not in cfg_permitidas:
            cfg = cfg_permitidas[0]

        # Ajustar calibre válido para el tipo
        cal_list = CALIBRES.get(tipo, CALIBRES_UNION)
        cal = str(row["Calibre"]) if row.get("Calibre") else (cal_list[0] if cal_list else "")
        if cal not in cal_list:
            cal = cal_list[0] if cal_list else cal

        # Longitud y total
        try:
            L = float(row.get("Longitud (m)", 0.0))
        except Exception:
            L = 0.0
        total = L * fases_de(cfg)

        processed.append({
            "Tipo": tipo,
            "Configuración": cfg,
            "Calibre": cal,
            "Longitud (m)": L,
            "Total Cable (m)": total,
        })

    df_out = pd.DataFrame(processed, columns=["Tipo", "Configuración", "Calibre", "Longitud (m)", "Total Cable (m)"])

    # ---- Persistir estados
    st.session_state["cables_proyecto_df"] = df_out.copy()
    lista = df_out.to_dict(orient="records")
    st.session_state["cables_proyecto"] = lista
    st.session_state.setdefault("datos_proyecto", {})
    st.session_state["datos_proyecto"]["cables_proyecto"] = lista

    # ---- Total global
    if not df_out.empty:
        st.markdown(f"**🧮 Total Global de Cable:** {df_out['Total Cable (m)'].sum():,.2f} m")

    return lista


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

