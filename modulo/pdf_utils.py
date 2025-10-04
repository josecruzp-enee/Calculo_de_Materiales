# -*- coding: utf-8 -*-
"""
pdf_utils.py
Generación de informes PDF del cálculo de materiales y estructuras
Autor: José Nikol Cruz
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

# --- Importación de tabla de cables ---
from modulo.configuracion_cables import tabla_cables_pdf

# ======== ESTILOS COMUNES ========
styles = getSampleStyleSheet()
styleN = ParagraphStyle(name="Normal9", parent=styles["Normal"], fontSize=9, leading=11)
styleH = styles["Heading1"]

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# === Fondo para todas las páginas ===
def fondo_pagina(canvas, doc):
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
    texto = str(nombre).strip().title()
    texto = re.sub(r"\bN[º°]?\s*(\d+)", r"N°\1", texto, flags=re.IGNORECASE)
    texto = texto.replace(" X ", " x ")
    return texto

# === Hoja de información del proyecto ===


# === Generar PDF de materiales globales ===
def generar_pdf_materiales(df_mat, nombre_proy, datos_proyecto=None):
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = [Paragraph(f"<b>Resumen de Materiales - Proyecto: {nombre_proy}</b>", styles["Title"]),
             Spacer(1, 12)]

    df_agrupado = df_mat.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
    data = [["Material", "Unidad", "Cantidad"]]
    for _, row in df_agrupado.iterrows():
        data.append([Paragraph(formatear_material(row["Materiales"]), styleN),
                     str(row["Unidad"]), f"{row['Cantidad']:.2f}"])

    tabla = Table(data, colWidths=[4*inch, 1*inch, 1*inch])
    tabla.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
    ]))
    elems.append(tabla)
    doc.build(elems)
    buffer.seek(0)
    return buffer

# === Generar estructuras global ===
def generar_pdf_estructuras_global(df_estructuras, nombre_proy):
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = [Paragraph(f"<b>Resumen de Estructuras - Proyecto: {nombre_proy}</b>", styles["Title"]),
             Spacer(1, 12)]
    data = [["Estructura", "Descripción", "Cantidad"]]
    for _, row in df_estructuras.iterrows():
        data.append([
            str(row.get("codigodeestructura", "")),
            str(row.get("Descripcion", "")),
            str(row.get("Cantidad", ""))
        ])
    tabla = Table(data, colWidths=[1.5*inch, 4*inch, 1*inch])
    tabla.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#003366")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke)
    ]))
    elems.append(tabla)
    doc.build(elems)
    buffer.seek(0)
    return buffer

# === Generar estructuras por punto ===
def generar_pdf_estructuras_por_punto(df_por_punto, nombre_proy):
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = [Paragraph(f"<b>Estructuras por Punto - Proyecto: {nombre_proy}</b>", styles["Title"]),
             Spacer(1, 12)]
    puntos = sorted(df_por_punto["Punto"].unique(), key=lambda x: int(re.sub(r'\D', '', str(x)) or 0))
    for p in puntos:
        elems.append(Paragraph(f"<b>Punto {p}</b>", styles["Heading2"]))
        df_p = df_por_punto[df_por_punto["Punto"] == p]
        data = [["Estructura", "Descripción", "Cantidad"]]
        for _, row in df_p.iterrows():
            data.append([str(row["codigodeestructura"]), str(row["Descripcion"]), str(row["Cantidad"])])
        tabla = Table(data, colWidths=[1.5*inch, 4*inch, 1*inch])
        tabla.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.black),
            ("BACKGROUND", (0,0), (-1,0), colors.lightblue),
            ("ALIGN", (2,1), (2,-1), "CENTER")
        ]))
        elems.append(tabla)
        elems.append(Spacer(1, 0.2*inch))
    doc.build(elems)
    buffer.seek(0)
    return buffer

# === Materiales adicionales ===
def agregar_tabla_materiales_adicionales(elems, datos_proyecto):
    df_extra = datos_proyecto.get("materiales_extra")
    if df_extra is None or df_extra.empty:
        return elems
    elems.append(PageBreak())
    elems.append(Paragraph("<b>Materiales Adicionales</b>", styles["Heading2"]))
    elems.append(Spacer(1, 12))
    data_extra = [["Material", "Unidad", "Cantidad"]]
    for _, row in df_extra.iterrows():
        data_extra.append([row["Materiales"], row["Unidad"], f"{row['Cantidad']:.2f}"])
    tabla = Table(data_extra, colWidths=[4*inch, 1*inch, 1*inch])
    tabla.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.orange),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke)
    ]))
    elems.append(tabla)
    return elems

# === Generar PDF de Materiales por Punto ===
def generar_pdf_materiales_por_punto(df_por_punto, nombre_proy):
    """Genera un PDF con materiales agrupados por punto."""
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="con_fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = []
    elems.append(Paragraph(f"<b>Materiales por Punto - Proyecto: {nombre_proy}</b>", styles["Title"]))
    elems.append(Spacer(1, 12))

    # Asegurar que los puntos estén ordenados correctamente
    puntos = sorted(df_por_punto["Punto"].unique(), key=lambda x: int(re.search(r'\d+', str(x)).group()))

    for p in puntos:
        elems.append(Paragraph(f"<b>Punto {p}</b>", styles["Heading2"]))
        df_p = df_por_punto[df_por_punto["Punto"] == p]
        df_agrupado = df_p.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

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
            ("BACKGROUND", (0,0), (-1,0), colors.darkgreen),
            ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
            ("ALIGN", (1,1), (-1,-1), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("FONTSIZE", (0,0), (-1,-1), 9),
        ]))

        elems.append(tabla)
        elems.append(Spacer(1, 0.2*inch))

    doc.build(elems)
    buffer.seek(0)
    return buffer

# === PDF completo consolidado ===
def generar_pdf_completo(df_mat, df_estructuras, df_estructuras_por_punto, df_mat_por_punto, datos_proyecto):
    """
    Genera un PDF completo consolidado con:
    - Hoja de información del proyecto
    - Resumen de materiales global (incluye cables)
    - Materiales adicionales
    - Tabla de cables
    - Resumen de estructuras global
    - Estructuras por punto
    - Materiales por punto
    """
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = []

    # === Hoja de información del proyecto ===
    elems += hoja_info_proyecto(datos_proyecto, df_estructuras, df_mat)

    # === Resumen global de materiales ===
    elems.append(Paragraph("<b>Resumen de Materiales</b>", styles["Heading2"]))

    df_agr = df_mat.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum() if not df_mat.empty else pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])

    # === Agregar los cables del proyecto al resumen de materiales ===
    if "cables_proyecto" in datos_proyecto and datos_proyecto["cables_proyecto"]:
        for cable in datos_proyecto["cables_proyecto"]:
            tipo = cable.get("Tipo", "")
            calibre = cable.get("Calibre", "")
            longitud = cable.get("Total Cable (m)", cable.get("Longitud (m)", 0))
            if longitud and calibre:
                descripcion = f"Cable {tipo} {calibre}"
                df_agr.loc[len(df_agr)] = [descripcion, "m", float(longitud)]

    # === Tabla de resumen de materiales ===
    data = [["Material", "Unidad", "Cantidad"]]
    for _, r in df_agr.iterrows():
        data.append([Paragraph(formatear_material(r["Materiales"]), styleN),
                     r["Unidad"],
                     f"{r['Cantidad']:.2f}"])

    tabla = Table(data, colWidths=[4*inch, 1*inch, 1*inch])
    tabla.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
    ]))
    elems.append(tabla)
    elems.append(PageBreak())

    # === Materiales adicionales ===
    elems = agregar_tabla_materiales_adicionales(elems, datos_proyecto)

    # === Tabla de cables ===
    from modulo.configuracion_cables import tabla_cables_pdf
    elems.extend(tabla_cables_pdf(datos_proyecto))

    # === Resumen de estructuras global ===
    if not df_estructuras.empty:
        elems.append(PageBreak())
        elems.append(Paragraph("<b>Resumen de Estructuras</b>", styles["Heading2"]))
        data_estruct = [["Estructura", "Descripción", "Cantidad"]]
        for _, row in df_estructuras.iterrows():
            data_estruct.append([
                str(row.get("codigodeestructura", "")),
                str(row.get("Descripcion", "")),
                str(row.get("Cantidad", ""))
            ])
        tabla_estruct = Table(data_estruct, colWidths=[1.5*inch, 4*inch, 1*inch])
        tabla_estruct.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.black),
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#003366")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
            ("ALIGN", (2,1), (2,-1), "CENTER")
        ]))
        elems.append(tabla_estruct)

    # === Estructuras por punto ===
    if not df_estructuras_por_punto.empty:
        elems.append(PageBreak())
        elems.append(Paragraph("<b>Estructuras por Punto</b>", styles["Heading2"]))
        for p in sorted(df_estructuras_por_punto["Punto"].unique(),
                        key=lambda x: int(re.sub(r'\D', '', str(x)) or 0)):
            elems.append(Paragraph(f"<b>Punto {p}</b>", styles["Heading3"]))
            df_p = df_estructuras_por_punto[df_estructuras_por_punto["Punto"] == p]
            data = [["Estructura", "Descripción", "Cantidad"]]
            for _, row in df_p.iterrows():
                data.append([
                    str(row["codigodeestructura"]),
                    str(row["Descripcion"]),
                    str(row["Cantidad"])
                ])
            tabla_p = Table(data, colWidths=[1.5*inch, 4*inch, 1*inch])
            tabla_p.setStyle(TableStyle([
                ("GRID", (0,0), (-1,-1), 0.5, colors.black),
                ("BACKGROUND", (0,0), (-1,0), colors.lightblue),
                ("ALIGN", (2,1), (2,-1), "CENTER")
            ]))
            elems.append(tabla_p)
            elems.append(Spacer(1, 0.2*inch))

    # === Materiales por punto ===
    if not df_mat_por_punto.empty:
        elems.append(PageBreak())
        elems.append(Paragraph("<b>Materiales por Punto</b>", styles["Heading2"]))
        puntos = sorted(df_mat_por_punto["Punto"].unique(),
                        key=lambda x: int(re.search(r'\d+', str(x)).group()))
        for p in puntos:
            elems.append(Paragraph(f"<b>Punto {p}</b>", styles["Heading3"]))
            df_p = df_mat_por_punto[df_mat_por_punto["Punto"] == p]
            df_agr_p = df_p.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
            data = [["Material", "Unidad", "Cantidad"]]
            for _, r in df_agr_p.iterrows():
                data.append([
                    Paragraph(formatear_material(r["Materiales"]), styleN),
                    str(r["Unidad"]),
                    f"{r['Cantidad']:.2f}"
                ])
            tabla_m = Table(data, colWidths=[4*inch, 1*inch, 1*inch])
            tabla_m.setStyle(TableStyle([
                ("GRID", (0,0), (-1,-1), 0.5, colors.black),
                ("BACKGROUND", (0,0), (-1,0), colors.darkgreen),
                ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
                ("ALIGN", (1,1), (-1,-1), "CENTER")
            ]))
            elems.append(tabla_m)
            elems.append(Spacer(1, 0.2*inch))

    # === Construcción final del PDF ===
    doc.build(elems)
    buffer.seek(0)
    return buffer




