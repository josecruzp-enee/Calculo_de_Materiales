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
    Dibuja el membrete como fondo superior.
    Selección vía st.session_state["membrete_pdf"]:
      - "SMART" -> data/Membrete_smart.png
      - "ENEE"  -> data/membrete_enee.jpg
    Ajuste de tamaño vía st.session_state["membrete_altura_in"]:
      - altura en pulgadas (float). Default: 1.10
    """
    try:
        canvas.saveState()

        # --- Import local para no amarrar reportlab a streamlit si no está ---
        try:
            import streamlit as st
            membrete = str(st.session_state.get("membrete_pdf", "SMART")).strip().upper()
            h_in = float(st.session_state.get("membrete_altura_in", 1.10))
        except Exception:
            membrete = "SMART"
            h_in = 1.10

        # --- Resolver archivo según opción ---
        if membrete == "ENEE":
            archivo = "membrete_enee.jpg"
        else:
            archivo = "Membrete_smart.png"   # tu nombre nuevo

        fondo = os.path.join(BASE_DIR, "data", archivo)

        ancho, alto = letter
        h = max(0.6, min(2.0, h_in)) * inch   # límite defensivo
        y = alto - h

        if os.path.exists(fondo):
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
