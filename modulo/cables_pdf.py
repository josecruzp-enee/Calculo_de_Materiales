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
    """
    elems = []
    try:
        from reportlab.platypus import Paragraph, Table, TableStyle, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        from reportlab.lib.units import inch
    except Exception:
        return elems

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

    # filtrar solo incluir
    if "Incluir" in df.columns:
        df = df[df["Incluir"].astype(bool)]

    if df.empty:
        return elems

    # columnas presentables
    cols = []
    for c in ["Tipo", "Calibre", "Config", "Conductores", "Longitud", "Unidad", "Descripcion"]:
        if c in df.columns:
            cols.append(c)

    df = df[cols].copy()

    styles = getSampleStyleSheet()
    elems.append(Paragraph("Cables del proyecto", styles["Heading3"]))
    elems.append(Spacer(1, 0.15 * inch))

    data = [cols]
    for _, r in df.iterrows():
        row = []
        for c in cols:
            v = r.get(c, "")
            v = "" if pd.isna(v) else str(v)
            row.append(escape(v))
        data.append(row)

    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    elems.append(t)
    elems.append(Spacer(1, 0.2 * inch))
    return elems
