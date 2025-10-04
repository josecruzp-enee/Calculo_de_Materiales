# -*- coding: utf-8 -*-
"""
pdf_utils.py
Generación de informes PDF del proyecto:
- Materiales
- Estructuras
- Materiales por punto
- Informe completo consolidado
Incluye integración con tabla de cables.
"""

from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime
from io import BytesIO
import os
import re
import pandas as pd
from modulo.configuracion_cables import tabla_cables_pdf  # integra sección cables

# ====== LOG UNIVERSAL ======
try:
    import streamlit as st
    log = st.write
except ImportError:
    log = print

# ======== ESTILOS COMUNES ========
styles = getSampleStyleSheet()
styleN = ParagraphStyle(name="Normal9", parent=styles["Normal"], fontSize=9, leading=11)
styleH = styles["Heading1"]

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # raíz del proyecto

# === Fondo para todas las páginas ===
def fondo_pagina(canvas, doc):
    """Dibuja el fondo con la imagen predeterminada."""
    try:
        canvas.saveState()
        fondo = os.path.join(BASE_DIR, "modulo", "Imagen Encabezado.jpg")
        ancho, alto = letter
        if os.path.exists(fondo):
            canvas.drawImage(fondo, 0, 0, width=ancho, height=alto, mask="auto")
        canvas.restoreState()
    except Exception as e:
        print(f"⚠️ Error aplicando fondo: {e}")

# === Formateo de materiales ===
def formatear_material(nombre):
    """Normaliza nombres de materiales."""
    texto = str(nombre).strip().title()
    texto = re.sub(r"\bN[º°]?\s*(\d+)", r"N°\1", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\bn(\d+)", r"N°\1", texto, flags=re.IGNORECASE)
    texto = texto.replace(" X ", " x ")
    return texto

# === Hoja de información del proyecto ===
def hoja_info_proyecto(datos_proyecto):
    elems = []
    elems.append(Paragraph("<b>Hoja de Información del Proyecto</b>", styleH))
    elems.append(Spacer(1, 12))

    data = [
        ["Nombre del Proyecto:", datos_proyecto.get("nombre_proyecto", "")],
        ["Código / Expediente:", datos_proyecto.get("codigo_proyecto", "")],
        ["Nivel de Tensión (kV):", datos_proyecto.get("nivel_de_tension", "")],
        ["Calibre Primario:", datos_proyecto.get("calibre_primario", "")],
        ["Calibre Secundario:", datos_proyecto.get("calibre_secundario", "")],
        ["Calibre Neutro:", datos_proyecto.get("calibre_neutro", "")],
        ["Calibre Piloto:", datos_proyecto.get("calibre_piloto", "")],
        ["Calibre Cable de Retenidas:", datos_proyecto.get("calibre_retenidas", "")],
        ["Fecha de Informe:", datetime.today().strftime("%d/%m/%Y")],
        ["Responsable / Diseñador:", datos_proyecto.get("responsable", "N/A")],
        ["Empresa / Área:", datos_proyecto.get("empresa", "N/A")],
    ]

    table = Table(data, colWidths=[180, 300])
    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (0,-1), colors.lightgrey),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
    ]))

    elems.append(table)
    elems.append(Spacer(1, 24))
    elems.append(PageBreak())
    return elems

# ======== FUNCIONES AUXILIARES ========
def ordenar_puntos(lista):
    """Ordena puntos de forma segura, numéricamente si aplica."""
    def clave(x):
        try:
            return int(re.search(r'\d+', str(x)).group())
        except:
            return float("inf")
    return sorted(lista, key=clave)

# ======== PDF DE MATERIALES ========
def generar_pdf_materiales(df_mat, nombre_proy, datos_proyecto=None):
    """Genera un PDF con el resumen global de materiales del proyecto."""
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="con_fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = []
    elems.append(Paragraph(f"<b>Resumen de Materiales - Proyecto: {nombre_proy}</b>", styles["Title"]))
    elems.append(Spacer(1, 12))

    df_agrupado = df_mat.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
    data = [["Material", "Unidad", "Cantidad"]]

    for _, row in df_agrupado.iterrows():
        data.append([
            Paragraph(formatear_material(row["Materiales"]), styleN),
            str(row["Unidad"]),
            f"{round(row['Cantidad'], 2):.2f}"
        ])

    tabla = Table(data, colWidths=[4*inch, 1*inch, 1*inch])
    tabla.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
    ]))
    elems.append(tabla)

    # Materiales adicionales
    if datos_proyecto and "materiales_extra" in datos_proyecto:
        df_extra = datos_proyecto["materiales_extra"]
        if df_extra is not None and not df_extra.empty:
            elems.append(Spacer(1, 24))
            elems.append(Paragraph("<b>Materiales Adicionales</b>", styles["Heading2"]))
            elems.append(Spacer(1, 12))

            data_extra = [["Material", "Unidad", "Cantidad"]]
            for _, row in df_extra.iterrows():
                data_extra.append([
                    Paragraph(formatear_material(row["Materiales"]), styleN),
                    str(row["Unidad"]),
                    f"{round(row['Cantidad'], 2):.2f}"
                ])

            tabla_extra = Table(data_extra, colWidths=[4*inch, 1*inch, 1*inch])
            tabla_extra.setStyle(TableStyle([
                ("GRID", (0,0), (-1,-1), 0.5, colors.black),
                ("BACKGROUND", (0,0), (-1,0), colors.orange),
                ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
                ("ALIGN", (1,1), (-1,-1), "CENTER"),
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                ("FONTSIZE", (0,0), (-1,-1), 9),
            ]))
            elems.append(tabla_extra)

    doc.build(elems)
    buffer.seek(0)
    return buffer

# ======== PDF ESTRUCTURAS GLOBALES ========
def generar_pdf_estructuras_global(df_estructuras, nombre_proy):
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = [Paragraph(f"<b>Resumen de Estructuras - Proyecto: {nombre_proy}</b>", styles["Title"]), Spacer(1, 12)]

    if df_estructuras is None or df_estructuras.empty:
        elems.append(Paragraph("No hay estructuras para mostrar.", styleN))
        doc.build(elems)
        buffer.seek(0)
        return buffer

    data = [["Estructura", "Descripción", "Cantidad"]]
    for _, row in df_estructuras.iterrows():
        data.append([
            str(row.get("codigodeestructura", "")),
            str(row.get("Descripcion", "")).capitalize(),
            str(row.get("Cantidad", ""))
        ])

    tabla = Table(data, colWidths=[1.5*inch, 4*inch, 1*inch])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.darkblue),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
    ]))

    elems.append(tabla)
    doc.build(elems)
    buffer.seek(0)
    return buffer

# ======== PDF COMPLETO ========
def generar_pdf_completo(df_mat, df_estructuras, df_estructuras_por_punto, df_materiales_por_punto, datos_proyecto):
    """Informe completo consolidado (incluye cables)."""
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="con_fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = []
    elems += hoja_info_proyecto(datos_proyecto)

    elems.append(Paragraph("<b>Resumen de Materiales</b>", styles["Heading2"]))
    elems.append(Spacer(1, 12))

    df_agrupado_mat = df_mat.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
    data_mat = [["Material", "Unidad", "Cantidad"]]
    for _, row in df_agrupado_mat.iterrows():
        data_mat.append([
            Paragraph(formatear_material(row["Materiales"]), styleN),
            str(row["Unidad"]),
            f"{round(row['Cantidad'], 2):.2f}"
        ])

    tabla_mat = Table(data_mat, colWidths=[250, 100, 100])
    tabla_mat.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
    ]))
    elems.append(tabla_mat)
    elems.append(PageBreak())

    # Estructuras, materiales adicionales y cables
    elems.extend(tabla_cables_pdf(datos_proyecto))
    doc.build(elems)
    buffer.seek(0)
    return buffer
