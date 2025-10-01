# modulos/pdf_utils.py

from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime
from io import BytesIO
import os
import re

# ======== ESTILOS COMUNES ========
styles = getSampleStyleSheet()
styleN = ParagraphStyle(name="Normal9", parent=styles["Normal"], fontSize=9, leading=11)
styleH = styles["Heading1"]

# === Fondo para todas las páginas ===
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # raíz del proyecto

def fondo_pagina(canvas, doc):
    """Coloca la imagen como fondo en toda la página"""
    canvas.saveState()
    fondo = os.path.join(BASE_DIR, "modulos", "Imagen Encabezado.jpg")
    ancho, alto = letter
    if os.path.exists(fondo):
        canvas.drawImage(fondo, 0, 0, width=ancho, height=alto, mask="auto")
    canvas.restoreState()

# === Formateo de materiales ===
def formatear_material(nombre):
    texto = str(nombre).strip().title()  # Mayúscula en cada palabra
    texto = re.sub(r"\bN[º°]?\s*(\d+)", r"N°\1", texto, flags=re.IGNORECASE)  # N°
    texto = re.sub(r"\bn(\d+)", r"N°\1", texto, flags=re.IGNORECASE)          # n6 → N°6
    texto = texto.replace(" X ", " x ")                                       # medidas
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


# ======== PDF GENERADORES ========

# modulos/pdf_utils.py

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

# ======== ESTILOS COMUNES ========
styles = getSampleStyleSheet()
styleN = ParagraphStyle(name="Normal9", parent=styles["Normal"], fontSize=9, leading=11)
styleH = styles["Heading1"]

# === Fondo para todas las páginas ===
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # raíz del proyecto

def fondo_pagina(canvas, doc):
    """Coloca la imagen como fondo en toda la página"""
    canvas.saveState()
    fondo = os.path.join(BASE_DIR, "modulos", "Imagen Encabezado.jpg")
    ancho, alto = letter
    if os.path.exists(fondo):
        canvas.drawImage(fondo, 0, 0, width=ancho, height=alto, mask="auto")
    canvas.restoreState()

# === Formateo de materiales ===
def formatear_material(nombre):
    texto = str(nombre).strip().title()  # Mayúscula en cada palabra
    texto = re.sub(r"\bN[º°]?\s*(\d+)", r"N°\1", texto, flags=re.IGNORECASE)  # N°6
    texto = re.sub(r"\bn(\d+)", r"N°\1", texto, flags=re.IGNORECASE)          # n6 → N°6
    texto = texto.replace(" X ", " x ")                                       # medidas
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


# ======== PDF GENERADORES ========

def generar_pdf_materiales(df_mat, nombre_proy, datos_proyecto=None):
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="con_fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = []

    if datos_proyecto:
        elems += hoja_info_proyecto(datos_proyecto)

    elems.append(Paragraph(f"<b>Resumen de Materiales - Proyecto: {nombre_proy}</b>", styles["Title"]))
    elems.append(Spacer(1, 12))

    data = [["Material", "Unidad", "Cantidad"]]
    for _, row in df_mat.iterrows():
        material = Paragraph(formatear_material(row["Materiales"]), styleN)
        unidad = str(row["Unidad"])
        cantidad = f"{round(row['Cantidad'], 2):.2f}"
        data.append([material, unidad, cantidad])

    tabla = Table(data, colWidths=[300, 100, 80])
    tabla.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
    ]))
    elems.append(tabla)

    doc.build(elems)
    buffer.seek(0)
    return buffer


def generar_pdf_estructuras(df_estructuras, nombre_proy):
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="con_fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = []

    elems.append(Paragraph(f"<b>Resumen de Estructuras - Proyecto: {nombre_proy}</b>", styles["Title"]))
    elems.append(Spacer(1, 12))

    data = [["Estructura", "Descripción", "Cantidad"]]
    for _, row in df_estructuras.iterrows():
        data.append([
            str(row["NombreEstructura"]),
            str(row["Descripcion"]).capitalize(),
            str(row["Cantidad"])
        ])

    tabla = Table(data, colWidths=[1.5*inch, 4*inch, 1*inch])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.darkblue),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("FONTSIZE", (0,0), (-1,-1), 9),
    ]))
    elems.append(tabla)

    doc.build(elems)
    buffer.seek(0)
    return buffer


def generar_pdf_materiales_por_punto(df_por_punto, nombre_proy):
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="con_fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = []

    elems.append(Paragraph(f"<b>Materiales por Punto - Proyecto: {nombre_proy}</b>", styles["Title"]))
    elems.append(Spacer(1, 12))

    puntos = sorted(df_por_punto["Punto"].unique(),
                    key=lambda x: int(re.search(r'\d+', str(x)).group()))

    for p in puntos:
        elems.append(Paragraph(f"<b>{p}</b>", styles["Heading2"]))
        df_p = df_por_punto[df_por_punto["Punto"] == p]

        data = [["Material", "Unidad", "Cantidad"]]
        for _, row in df_p.iterrows():
            data.append([
                Paragraph(formatear_material(row["Materiales"]), styleN),
                str(row["Unidad"]),
                str(round(row["Cantidad"], 2))
            ])

        tabla = Table(data, colWidths=[4*inch, 1*inch, 1*inch])
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.darkgreen),
            ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
            ("GRID", (0,0), (-1,-1), 0.5, colors.black),
            ("FONTSIZE", (0,0), (-1,-1), 9),
        ]))
        elems.append(tabla)
        elems.append(Spacer(1, 0.3 * inch))

    doc.build(elems)
    buffer.seek(0)
    return buffer


def generar_pdf_completo(df_mat, df_estructuras, df_por_punto, datos_proyecto):
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="con_fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = []

    # 1. Portada
    elems += hoja_info_proyecto(datos_proyecto)

    # 2. Resumen materiales
    elems.append(Paragraph("<b>Resumen de Materiales</b>", styles["Heading2"]))
    elems.append(Spacer(1, 12))

    data_mat = [["Material", "Unidad", "Cantidad"]]
    for _, row in df_mat.iterrows():
        data_mat.append([
            Paragraph(formatear_material(row["Materiales"]), styleN),
            str(row["Unidad"]),
            str(round(row["Cantidad"], 2))
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

    # 3. Resumen estructuras
    elems.append(Paragraph("<b>Resumen de Estructuras</b>", styles["Heading2"]))
    elems.append(Spacer(1, 12))

    data_est = [["Estructura", "Descripción", "Cantidad"]]
    for _, row in df_estructuras.iterrows():
        data_est.append([
            str(row["NombreEstructura"]),
            str(row["Descripcion"]).capitalize(),
            str(row["Cantidad"])
        ])

    tabla_est = Table(data_est, colWidths=[150, 300, 100])
    tabla_est.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("ALIGN", (2,1), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
    ]))
    elems.append(tabla_est)
    elems.append(PageBreak())

    # 4. Materiales por punto
    elems.append(Paragraph("<b>Materiales por Punto</b>", styles["Heading2"]))
    elems.append(Spacer(1, 12))

    data_punto = [["Punto", "Material", "Unidad", "Cantidad"]]
    puntos = sorted(df_por_punto["Punto"].unique(),
                    key=lambda x: int(re.search(r'\d+', str(x)).group()))

    for p in puntos:
        df_p = df_por_punto[df_por_punto["Punto"] == p]
        for _, row in df_p.iterrows():
            data_punto.append([
                str(p),
                Paragraph(formatear_material(row["Materiales"]), styleN),
                str(row["Unidad"]),
                str(row["Cantidad"])
            ])

    tabla_punto = Table(data_punto, colWidths=[80, 220, 80, 80])
    tabla_punto.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("ALIGN", (2,1), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
    ]))
    elems.append(tabla_punto)

    doc.build(elems)
    buffer.seek(0)
    return buffer
