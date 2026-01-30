# -*- coding: utf-8 -*-
"""
cables_pdf.py
Render de la tabla de cables para PDF (ReportLab).
"""

from __future__ import annotations
import pandas as pd
from xml.sax.saxutils import escape


def tabla_cables_pdf(datos_proyecto: dict):
    """
    Devuelve lista de flowables ReportLab (Paragraph/Table/Spacer) para insertar en PDF.
    Toma fuente desde:
      - st.session_state["cables_proyecto"] (lista)
      - st.session_state["cables_proyecto_df"] (df)
      - datos_proyecto["cables_proyecto"]

    PDF (solo estas columnas):
      Tipo | Configuración | Calibre | Longitud (m) | Total Cable (m)
    """
    elems = []
    try:
        from reportlab.platypus import Paragraph, Table, TableStyle, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        from reportlab.lib.units import inch
    except Exception:
        return elems

    # ----------------------------
    # 1) Obtener fuente de datos
    # ----------------------------
    fuente = None
    try:
        import streamlit as st
        if isinstance(st.session_state.get("cables_proyecto"), list) and st.session_state["cables_proyecto"]:
            fuente = st.session_state["cables_proyecto"]
        elif isinstance(st.session_state.get("cables_proyecto_df"), pd.DataFrame) and not st.session_state["cables_proyecto_df"].empty:
            fuente = st.session_state["cables_proyecto_df"].to_dict(orient="records")
    except Exception:
        fuente = None

    if not fuente:
        lista_dp = (datos_proyecto or {}).get("cables_proyecto", [])
        if isinstance(lista_dp, list) and lista_dp:
            fuente = lista_dp

    if not fuente:
        return elems

    df = pd.DataFrame(fuente).copy()
    if df.empty:
        return elems

    # ----------------------------
    # 2) Normalizar nombres de columnas
    # ----------------------------
    # Acepta posibles nombres alternos
    rename_map = {
        "Config": "Configuración",
        "Configuración": "Configuración",
        "Longitud": "Longitud (m)",
        "Longitud (m)": "Longitud (m)",
        "Total": "Total Cable (m)",
        "Total Cable (m)": "Total Cable (m)",
    }
    df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)

    # Asegurar columnas base
    if "Tipo" not in df.columns:
        df["Tipo"] = ""
    if "Calibre" not in df.columns:
        df["Calibre"] = ""
    if "Configuración" not in df.columns:
        df["Configuración"] = ""
    if "Longitud (m)" not in df.columns:
        df["Longitud (m)"] = 0.0

    df["Tipo"] = df["Tipo"].astype(str).str.strip()
    df["Calibre"] = df["Calibre"].astype(str).str.strip()
    df["Configuración"] = df["Configuración"].astype(str).str.strip()
    df["Longitud (m)"] = pd.to_numeric(df["Longitud (m)"], errors="coerce").fillna(0.0)

    # ----------------------------
    # 3) Total Cable (m)
    # ----------------------------
    # Si existe Conductores y no existe Total, lo calculamos.
    if "Total Cable (m)" not in df.columns:
        if "Conductores" in df.columns:
            cond = pd.to_numeric(df["Conductores"], errors="coerce").fillna(0.0)
            df["Total Cable (m)"] = df["Longitud (m)"].astype(float) * cond.astype(float)
        else:
            df["Total Cable (m)"] = df["Longitud (m)"].astype(float)
    else:
        # Si existe pero trae NaN, rellenar:
        df["Total Cable (m)"] = pd.to_numeric(df["Total Cable (m)"], errors="coerce")
        mask = df["Total Cable (m)"].isna()
        if mask.any():
            if "Conductores" in df.columns:
                cond = pd.to_numeric(df["Conductores"], errors="coerce").fillna(0.0)
                df.loc[mask, "Total Cable (m)"] = df.loc[mask, "Longitud (m)"].astype(float) * cond.loc[mask].astype(float)
            else:
                df.loc[mask, "Total Cable (m)"] = df.loc[mask, "Longitud (m)"].astype(float)

    # Filtrar filas vacías (mínimo tipo + calibre)
    df = df[(df["Tipo"] != "") & (df["Calibre"] != "")]
    if df.empty:
        return elems

    # Solo columnas deseadas en el PDF
    cols = ["Tipo", "Configuración", "Calibre", "Longitud (m)", "Total Cable (m)"]
    df = df[cols].copy()

    # ----------------------------
    # 4) Armar tabla PDF
    # ----------------------------
    styles = getSampleStyleSheet()
    elems.append(Paragraph("Cables del proyecto", styles["Heading3"]))
    elems.append(Spacer(1, 0.15 * inch))

    data = [[
        "Tipo",
        "Configuración",
        "Calibre",
        "Longitud (m)",
        "Total Cable (m)",
    ]]

    for _, r in df.iterrows():
        data.append([
            escape(str(r["Tipo"])),
            escape(str(r["Configuración"])),
            escape(str(r["Calibre"])),
            f"{float(r['Longitud (m)']):.2f}",
            f"{float(r['Total Cable (m)']):.2f}",
        ])

    t = Table(
        data,
        repeatRows=1,
        colWidths=[0.9 * inch, 1.2 * inch, 2.6 * inch, 1.1 * inch, 1.2 * inch],
    )
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (3, 1), (-1, -1), "RIGHT"),  # números a la derecha
    ]))

    elems.append(t)
    elems.append(Spacer(1, 0.15 * inch))

    total_global = float(df["Total Cable (m)"].sum())
    elems.append(Paragraph(f"<b>Total global:</b> {total_global:,.2f} m", styles["Normal"]))
    elems.append(Spacer(1, 0.10 * inch))

    return elems
