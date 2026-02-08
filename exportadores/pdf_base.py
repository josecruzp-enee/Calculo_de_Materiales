# -*- coding: utf-8 -*-
"""
exportadores/pdf_base.py
Base común para PDFs: estilos, helpers, membrete, calibres.
Autor: José Nikol Cruz
"""

from reportlab.platypus import PageBreak
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import os
import pandas as pd
from xml.sax.saxutils import escape


# ======== ESTILOS COMUNES ========
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
# FIX: formatear_material (IDENTIDAD)
# ==========================================================
def formatear_material(nombre):
    """Convierte a texto seguro para Paragraph."""
    if nombre is None or (isinstance(nombre, float) and pd.isna(nombre)):
        return ""
    return escape(str(nombre).strip())


# ==========================
# HELPERS (ANTI PÁGINAS EN BLANCO)
# ==========================
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


# ==========================
# FONDO DE PÁGINA (MEMBRETE)
# ==========================
def fondo_pagina(canvas, doc):
    """
    Dibuja el membrete seleccionado en la parte superior.
    Lee primero st.session_state (si existe) y si no, usa atributos del doc.
    """
    try:
        import streamlit as st

        canvas.saveState()

        # 1) prioridad: session_state (tu radio/select)
        membrete = None
        try:
            if "membrete_pdf" in st.session_state:
                membrete = st.session_state.get("membrete_pdf")
            elif "membrete_pdf_val" in st.session_state:
                membrete = st.session_state.get("membrete_pdf_val")
        except Exception:
            membrete = None

        # 2) fallback: atributos del doc
        if not membrete:
            membrete = getattr(doc, "membrete_pdf", None) or getattr(doc, "membrete_pdf_val", None)

        membrete = str(membrete or "SMART").strip().upper()

        fondo = os.path.join(
            BASE_DIR, "data",
            "membrete_enee.jpg" if membrete == "ENEE" else "Membrete_smart.png"
        )

        ancho, alto = letter

        if os.path.exists(fondo):
            if membrete == "ENEE":
        # ENEE = fondo completo (hoja membretada / marca de agua)
        canvas.drawImage(
            fondo,
            0, 0,
            width=ancho,
            height=alto,
            preserveAspectRatio=True,
            anchor="c",
            mask="auto",
        )
    else:
        # SMART = solo encabezado (membrete)
        h = 1.05 * inch
        y = alto - h
        canvas.drawImage(
            fondo,
            0, y,
            width=ancho,
            height=h,
            preserveAspectRatio=True,
            anchor="n",
            mask="auto",
        )


        canvas.restoreState()

    except Exception as e:
        try:
            canvas.restoreState()
        except Exception:
            pass
        print(f"⚠️ Error aplicando fondo: {e}")





# ==========================================================
# CALIBRES desde tabla de Cables (sin longitudes)
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


def _calibres_por_tipo(cables, tipo_buscar: str) -> str:
    """
    Devuelve calibres únicos separados por coma para un tipo de cable:
    MT, BT, N, HP, RETENIDA.
    Lee claves flexibles: "Tipo"/"tipo" y "Calibre"/"calibre".
    """
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
