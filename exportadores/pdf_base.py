# -*- coding: utf-8 -*-
"""
exportadores/pdf_base.py
Base común para PDFs: estilos, helpers, membrete, calibres.
Autor: José Nikol Cruz
"""

from reportlab.platypus import PageBreak, TableStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import os
import pandas as pd
from xml.sax.saxutils import escape


# ==========================================================
# ESTILOS COMUNES
# ==========================================================
styles = getSampleStyleSheet()

styleN = ParagraphStyle(
    name="Normal9",
    parent=styles["Normal"],
    fontSize=9,
    leading=11
)

styleH = styles["Heading1"]

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# ==========================================================
# 🎯 ESTILO DE TABLA UNIFORME (NUEVO)
# ==========================================================
def estilo_tabla():
    return TableStyle([

        # HEADER (AZUL PROFESIONAL)
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),

        # CUERPO
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),

        # ALINEACIÓN
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        # FILAS ALTERNADAS (PRO)
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#F2F2F2")]),

        # BORDES
        ("GRID", (0, 0), (-1, -1), 0.4, colors.black),

        # PADDING
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ])


# ==========================================================
# FIX: FORMATEAR MATERIAL
# ==========================================================
def formatear_material(nombre):
    if nombre is None or (isinstance(nombre, float) and pd.isna(nombre)):
        return ""
    return escape(str(nombre).strip())


# ==========================================================
# HELPERS (ANTI PÁGINAS EN BLANCO)
# ==========================================================
def salto_pagina_seguro(elems):
    if elems and not isinstance(elems[-1], PageBreak):
        elems.append(PageBreak())


def extender_flowables(elems, extra):
    if not extra:
        return elems
    if elems and isinstance(elems[-1], PageBreak) and isinstance(extra[0], PageBreak):
        extra = extra[1:]
    elems.extend(extra)
    return elems


def quitar_saltos_finales(elems):
    while elems and isinstance(elems[-1], PageBreak):
        elems.pop()
    return elems


# ==========================================================
# FONDO DE PÁGINA (MEMBRETE)
# ==========================================================
def fondo_pagina(canvas, doc):

    try:
        import streamlit as st

        canvas.saveState()

        membrete = None

        try:
            if "membrete_pdf" in st.session_state:
                membrete = st.session_state.get("membrete_pdf")
            elif "membrete_pdf_val" in st.session_state:
                membrete = st.session_state.get("membrete_pdf_val")
        except Exception:
            membrete = None

        if not membrete:
            membrete = getattr(doc, "membrete_pdf", None) or getattr(doc, "membrete_pdf_val", None)

        membrete = str(membrete or "SMART").strip().upper()

        BASE_DIR = os.path.dirname(os.path.dirname(__file__))

        if membrete == "ENEE":
            fondo = os.path.join(BASE_DIR, "data", "membrete_enee.jpg")
        elif membrete == "ROMARIO":
            fondo = os.path.join(BASE_DIR, "data", "logo_romario.png")
        else:
            fondo = os.path.join(BASE_DIR, "data", "Membrete_smart.png")

        ancho, alto = letter

        if os.path.exists(fondo):

            if membrete == "ENEE":
                canvas.drawImage(fondo, 0, 0, width=ancho, height=alto)

            elif membrete == "SMART":
                h = 1.05 * inch
                canvas.drawImage(fondo, 0, alto - h, width=ancho, height=h)

            elif membrete == "ROMARIO":
                h = 1.2 * inch
                canvas.drawImage(fondo, 0, alto - h, width=ancho, height=h)

        canvas.restoreState()

    except Exception as e:
        try:
            canvas.restoreState()
        except Exception:
            pass

        print(f"⚠️ Error aplicando fondo: {e}")


# ==========================================================
# CALIBRES
# ==========================================================
def _dedupe_keep_order(vals):
    seen = set()
    out = []
    for v in vals:
        k = str(v).strip().upper()
        if not k:
            continue
        if k in seen:
            continue
        seen.add(k)
        out.append(str(v).strip())
    return out


def _calibres_por_tipo(cables, tipo_buscar: str):

    t = (tipo_buscar or "").strip().upper()

    if not cables:
        return ""

    calibres = []

    for c in cables:
        tipo = str(c.get("Tipo", c.get("tipo", ""))).strip().upper()

        if tipo != t:
            continue

        cal = str(c.get("Calibre", c.get("calibre", ""))).strip()

        if cal:
            calibres.append(cal)

    calibres = _dedupe_keep_order(calibres)

    return ", ".join(calibres)
