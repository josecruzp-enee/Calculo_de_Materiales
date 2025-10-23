# -*- coding: utf-8 -*-
"""
configuracion_cables.py
Sección Streamlit para gestionar tramos de cable como TABLA editable.
Guarda en:
- st.session_state["cables_proyecto_df"]  (DataFrame)
- st.session_state["cables_proyecto"]     (lista de dicts)
- st.session_state["datos_proyecto"]["cables_proyecto"] (para PDF)
Incluye tabla_cables_pdf(datos_proyecto) para ReportLab.
"""

import streamlit as st
import pandas as pd

# ReportLab (solo si generas PDF; si no está instalado, puedes envolver en try/except en tu app principal)
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch


# =========================
# Catálogos y reglas
# =========================
TIPOS = ["MT", "BT", "N", "HP", "Retenida"]

# Calibres por tipo (Retenida como pediste: 1/4, 5/8, 3/4)
CALIBRES = {
    "MT": ["2 ASCR", "1/0 ASCR", "2/0 ASCR", "3/0 ASCR", "4/0 ASCR", "266.8 MCM", "336 MCM"],
    "BT": ["2 WP", "1/0 WP", "2/0 WP", "3/0 WP", "4/0 WP"],
    "N":  ["2 ASCR", "1/0 ASCR", "2/0 ASCR", "3/0 ASCR", "4/0 ASCR"],
    "HP": ["2 WP", "1/0 WP", "2/0 WP"],
    "Retenida": ["1/4", "5/8", "3/4"],
}

# Configuraciones permitidas por tipo (según tu requerimiento)
CONFIGS_BY_TIPO = {
    "MT": ["1F", "2F", "3F"],
    "BT": ["1F", "2F", "3F"],
    "N":  ["N"],
    "HP": ["1F+N", "2F"],
    "Retenida": ["Única"],
}

# Conjuntos globales para el editor (luego validamos por fila)
CONFIGS_UNION = ["Única", "N", "1F", "1F+N", "2F", "3F"]
CALIBRES_UNION = list(dict.fromkeys(c for lst in CALIBRES.values() for c in lst))  # orden estable

# Cuántos conductores se usan en el cálculo de "Total Cable (m)" según configuración
def conductores_de(cfg: str) -> int:
    if not isinstance(cfg, str):
        return 1
    c = cfg.strip().upper()
    if c in ("ÚNICA", "N", "1F"):
        return 1
    if c == "1F+N":
        return 2
    if c == "2F":
        return 2
    if c == "3F":
        return 3
    return 1


# =========================
# 1️⃣ Sección Streamlit (tabla)
# =========================
def seccion_cables():
    """Interfaz Streamlit como TABLA editable para configurar tramos de cable."""
    st.markdown("### 2️⃣ ⚡ Configuración y calibres de conductores (tabla)")

    # ---- Estado inicial: DataFrame vacío con columnas destino
    if "cables_proyecto_df" not in st.session_state:
        st.session_state["cables_proyecto_df"] = pd.DataFrame(
            columns=["Tipo", "Configuración", "Calibre", "Longitud (m)", "Total Cable (m)"]
        )

    # ---- Normalización en caliente de etiquetas antiguas a las nuevas ----
    # (Si en memoria aún quedan 'Primario', 'Secundario', etc.)
    mapa_tipos = {
        "Primario": "MT",
        "Secundario": "BT",
        "Neutro": "N",
        "Piloto": "HP",
        "Retenidas": "Retenida",
    }

    df_prev = st.session_state.get("cables_proyecto_df")
    if df_prev is not None and not df_prev.empty and "Tipo" in df_prev.columns:
        st.session_state["cables_proyecto_df"]["Tipo"] = df_prev["Tipo"].replace(mapa_tipos)

    lista_prev = st.session_state.get("cables_proyecto")
    if lista_prev:
        for r in lista_prev:
            if isinstance(r, dict) and "Tipo" in r and r["Tipo"] in mapa_tipos:
                r["Tipo"] = mapa_tipos[r["Tipo"]]
        if df_prev is None or (hasattr(df_prev, "empty") and df_prev.empty):
            st.session_state["cables_proyecto_df"] = pd.DataFrame(lista_prev)

    dp = st.session_state.get("datos_proyecto", {})
    cp_dp = dp.get("cables_proyecto")
    if isinstance(cp_dp, list):
        for r in cp_dp:
            if isinstance(r, dict) and "Tipo" in r and r["Tipo"] in mapa_tipos:
                r["Tipo"] = mapa_tipos[r["Tipo"]]
        if st.session_state.get("cables_proyecto_df") is None or st.session_state["cables_proyecto_df"].empty:
            st.session_state["cables_proyecto_df"] = pd.DataFrame(cp_dp)

    # Si está vacío, agrega una fila inicial para guiar
    if st.session_state["cables_proyecto_df"].empty:
        st.session_state["cables_proyecto_df"] = pd.DataFrame([{
            "Tipo": "MT", "Configuración": "1F", "Calibre": "1/0 ASCR",
            "Longitud (m)": 0.0, "Total Cable (m)": 0.0
        }])

    st.caption("Agrega/edita filas; el **Total** se calcula automáticamente según la configuración.")

    # --- Editor de tabla dinámico ---
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
                help="MT/BT: 1F/2F/3F · N: N · HP: 1F+N/2F · Retenida: Única",
            ),
            "Calibre": st.column_config.SelectboxColumn(
                "Calibre", options=CALIBRES_UNION, required=True, width="medium",
            ),
            "Longitud (m)": st.column_config.NumberColumn(
                "Longitud (m)", min_value=0.0, step=10.0, format="%.2f",
            ),
            "Total Cable (m)": st.column_config.NumberColumn(
                "Total Cable (m)", disabled=True, format="%.2f",
                help="Longitud × Nº de conductores (autocalculado)",
            ),
        },
        hide_index=True,
    )

    # --- Validación por fila + cálculo de total ---
    processed_rows = []
    for _, row in edited_df.fillna("").iterrows():
        if not row.get("Tipo"):
            continue
        tipo = str(row["Tipo"])

        # Ajustar configuración permitida por tipo
        cfg_permitidas = CONFIGS_BY_TIPO.get(tipo, ["Única"])
        cfg = str(row["Configuración"]) if row.get("Configuración") else cfg_permitidas[0]
        if cfg not in cfg_permitidas:
            cfg = cfg_permitidas[0]

        # Ajustar calibre válido por tipo
        cal_list = CALIBRES.get(tipo, CALIBRES_UNION)
        cal = str(row["Calibre"]) if row.get("Calibre") else (cal_list[0] if cal_list else "")
        if cal not in cal_list:
            cal = cal_list[0] if cal_list else cal

        # Longitud y total
        try:
            L = float(row.get("Longitud (m)", 0.0))
        except Exception:
            L = 0.0

        total = L * conductores_de(cfg)

        processed_rows.append({
            "Tipo": tipo,
            "Configuración": cfg,
            "Calibre": cal,
            "Longitud (m)": L,
            "Total Cable (m)": total,
        })

    df_out = pd.DataFrame(processed_rows, columns=["Tipo", "Configuración", "Calibre", "Longitud (m)", "Total Cable (m)"])

    # ---- Persistir estados coherentes
    st.session_state["cables_proyecto_df"] = df_out.copy()

    lista = df_out.to_dict(orient="records")
    st.session_state["cables_proyecto"] = lista
    st.session_state.setdefault("datos_proyecto", {})
    st.session_state["datos_proyecto"]["cables_proyecto"] = lista

    # ---- Total global
    if not df_out.empty:
        total_global = df_out["Total Cable (m)"].sum()
        st.markdown(f"**🧮 Total Global de Cable:** {total_global:,.2f} m")

    return lista


# =========================
# 2️⃣ Tabla para PDF (ReportLab)
# =========================
def tabla_cables_pdf(datos_proyecto):
    """
    Genera elementos ReportLab (tabla + totales) para insertar en el PDF.
    Lee de datos_proyecto["cables_proyecto"] y, si existe, refleja lo último en session_state.
    """
    elems = []
    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    styleH = styles["Heading2"]

    # Toma siempre la última versión en memoria si existe
    if st.session_state.get("cables_proyecto"):
        datos_proyecto = dict(datos_proyecto or {})
        datos_proyecto["cables_proyecto"] = st.session_state["cables_proyecto"]

    filas = (datos_proyecto or {}).get("cables_proyecto", [])
    if not filas:
        return elems

    df = pd.DataFrame(filas, columns=["Tipo", "Configuración", "Calibre", "Longitud (m)", "Total Cable (m)"])
    if df.empty:
        return elems

    elems.append(Spacer(1, 0.2 * inch))
    elems.append(Paragraph("⚡ Configuración y Calibres de Conductores", styleH))
    elems.append(Spacer(1, 0.1 * inch))

    data = [["Tipo", "Configuración", "Calibre", "Longitud (m)", "Total Cable (m)"]]
    for _, row in df.iterrows():
        data.append([
            str(row.get("Tipo", "")),
            str(row.get("Configuración", "")),
            str(row.get("Calibre", "")),
            f"{float(row.get('Longitud (m)', 0.0)):.2f}",
            f"{float(row.get('Total Cable (m)', 0.0)):.2f}",
        ])

    tabla = Table(data, colWidths=[1.2 * inch] * 5)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
    ]))

    elems.append(tabla)
    elems.append(Spacer(1, 0.15 * inch))

    total_global = df["Total Cable (m)"].sum()
    elems.append(Paragraph(f"🧮 <b>Total Global de Cable:</b> {total_global:,.2f} m", styleN))
    elems.append(Spacer(1, 0.25 * inch))
    return elems
