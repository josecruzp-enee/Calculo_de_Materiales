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
import pandas as pd

# ======== ESTILOS COMUNES ========
styles = getSampleStyleSheet()
styleN = ParagraphStyle(name="Normal9", parent=styles["Normal"], fontSize=9, leading=11)
styleH = styles["Heading1"]

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # raíz del proyecto

# === Fondo para todas las páginas ===
def fondo_pagina(canvas, doc):
    try:
        canvas.saveState()
        fondo = os.path.join(BASE_DIR, "modulos", "Imagen Encabezado.jpg")
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
    texto = re.sub(r"\bn(\d+)", r"N°\1", texto, flags=re.IGNORECASE)  # n6 → N°6
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
            return float("inf")  # Los que no tienen número al final
    return sorted(lista, key=clave)

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

def generar_pdf_estructuras_global(df_estructuras, nombre_proy):
    """
    Genera un PDF con el resumen total de estructuras (sumadas),
    sin separar por puntos.
    """
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


def generar_pdf_estructuras_por_punto(df_por_punto, nombre_proy):
    """
    Genera un PDF de estructuras agrupadas por Punto.
    Cada punto aparece como fila centrada y debajo sus estructuras.
    """
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="con_fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = []
    elems.append(Paragraph(f"<b>Estructuras por Punto - Proyecto: {nombre_proy}</b>", styles["Title"]))
    elems.append(Spacer(1, 12))

    data = [["Estructura", "Descripción", "Cantidad"]]

    # Recorremos por punto
    puntos = df_por_punto["Punto"].unique()
    for p in puntos:
        # Fila de título del punto
        data.append([f"Punto {p}", "", ""])
        # Filas de estructuras
        df_p = df_por_punto[df_por_punto["Punto"] == p]
        for _, row in df_p.iterrows():
            data.append([
                str(row["NombreEstructura"]),
                str(row["Descripcion"]).capitalize(),
                str(row["Cantidad"])
            ])

    tabla = Table(data, colWidths=[1.5*inch, 4*inch, 1*inch])

    # Estilos
    estilos = [
        ("BACKGROUND", (0,0), (-1,0), colors.darkblue),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
    ]

    # 🔹 Estilos especiales para filas de "Punto N"
    row_idx = 1
    for p in puntos:
        estilos += [
            ("SPAN", (0,row_idx), (-1,row_idx)),  # fusionar toda la fila
            ("BACKGROUND", (0,row_idx), (-1,row_idx), colors.lightblue),
            ("TEXTCOLOR", (0,row_idx), (-1,row_idx), colors.black),
            ("ALIGN", (0,row_idx), (-1,row_idx), "CENTER"),
            ("FONTNAME", (0,row_idx), (-1,row_idx), "Helvetica-Bold")
        ]
        row_idx += 1 + len(df_por_punto[df_por_punto["Punto"] == p])

    tabla.setStyle(TableStyle(estilos))
    elems.append(tabla)

    doc.build(elems)
    buffer.seek(0)
    return buffer

def generar_pdf_materiales_por_punto(df_por_punto, nombre_proy, estructuras_por_punto=None, df_indice=None):
    """
    Genera un PDF de materiales por punto, sumando cantidades si un punto se repite.
    """
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="con_fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = []
    elems.append(Paragraph(f"<b>Materiales por Punto - Proyecto: {nombre_proy}</b>", styles["Title"]))
    elems.append(Spacer(1, 12))

    # Obtener los puntos únicos
    puntos = sorted(df_por_punto["Punto"].unique(), key=lambda x: int(re.search(r'\d+', str(x)).group()))

    for p in puntos:
        punto_num = str(p).replace("Punto", "").strip()
        elems.append(Paragraph(f"<b>Punto {punto_num}</b>", styles["Heading2"]))

        # Mostrar código y descripción de estructuras si existe
        if estructuras_por_punto and df_indice is not None and p in estructuras_por_punto:
            for cod in estructuras_por_punto[p]:
                desc = ""
                if cod in df_indice["NombreEstructura"].values:
                    desc = df_indice.loc[df_indice["NombreEstructura"] == cod, "Descripcion"].values[0]
                elems.append(Paragraph(f"{cod}", styleN))
                elems.append(Paragraph(f"{desc}", styleN))
            elems.append(Spacer(1, 6))

        # --- AGRUPAR MATERIALES POR PUNTO ---
        df_agrupado = df_por_punto[df_por_punto["Punto"] == p].groupby(
            ["Materiales", "Unidad"], as_index=False
        ).sum(numeric_only=True)

        # Construir tabla
        data = [["Material", "Unidad", "Cantidad"]]
        for _, row in df_agrupado.iterrows():
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
            ("ALIGN", (1,1), (-1,-1), "CENTER"),
        ]))
        elems.append(tabla)
        elems.append(Spacer(1, 0.3 * inch))

    doc.build(elems)
    buffer.seek(0)
    return buffer


def generar_pdf_completo(df_mat, df_estructuras, df_por_punto, datos_proyecto):
    """
    Genera el informe completo en PDF en este orden:
    1. Portada con información del proyecto
    2. Resumen de materiales (global)
    3. Estructuras por punto
    4. Resumen de estructuras (global)
    5. Materiales por punto
    """
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="con_fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])
    elems = []

    # 1️⃣ Portada
    elems += hoja_info_proyecto(datos_proyecto)

    # 2️⃣ Resumen de materiales (global)
    elems.append(Paragraph("<b>Resumen de Materiales</b>", styles["Heading2"]))
    elems.append(Spacer(1, 12))

    df_agrupado_mat = df_mat.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
    data_mat = [["Material", "Unidad", "Cantidad"]]
    for _, row in df_agrupado_mat.iterrows():
        data_mat.append([Paragraph(formatear_material(row["Materiales"]), styleN),
                         row["Unidad"],
                         round(row["Cantidad"], 2)])
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

    # 3️⃣ Estructuras por punto
    elems.append(Paragraph("<b>Estructuras por Punto</b>", styles["Heading2"]))
    elems.append(Spacer(1, 12))

    data_est_p = [["Estructura", "Descripción", "Cantidad"]]
    puntos = df_por_punto["Punto"].unique()
    for p in puntos:
        data_est_p.append([f"Punto {p}", "", ""])
        df_p = df_por_punto[df_por_punto["Punto"] == p]
        for _, row in df_p.iterrows():
            data_est_p.append([
                str(row["NombreEstructura"]),
                str(row["Descripcion"]).capitalize(),
                str(row["Cantidad"])
            ])

    tabla_est_p = Table(data_est_p, colWidths=[150, 300, 100])

    estilos = [
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("ALIGN", (2,1), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
    ]
    row_idx = 1
    for p in puntos:
        estilos += [
            ("SPAN", (0,row_idx), (-1,row_idx)),
            ("BACKGROUND", (0,row_idx), (-1,row_idx), colors.lightblue),
            ("ALIGN", (0,row_idx), (-1,row_idx), "CENTER"),
            ("FONTNAME", (0,row_idx), (-1,row_idx), "Helvetica-Bold")
        ]
        row_idx += 1 + len(df_por_punto[df_por_punto["Punto"] == p])

    tabla_est_p.setStyle(TableStyle(estilos))
    elems.append(tabla_est_p)
    elems.append(PageBreak())

    # 4️⃣ Resumen de estructuras (global)
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

    # 5️⃣ Materiales por punto
    elems.append(Paragraph("<b>Materiales por Punto</b>", styles["Heading2"]))
    elems.append(Spacer(1, 12))

    puntos = sorted(df_por_punto["Punto"].unique(), key=lambda x: int(re.search(r'\d+', str(x)).group()))
    for p in puntos:
        punto_num = str(p).replace("Punto", "").strip()
        elems.append(Paragraph(f"<b>Punto {punto_num}</b>", styles["Heading2"]))

        df_p = df_por_punto[df_por_punto["Punto"] == p]
        df_agrupado = df_p.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

        data_punto = [["Material", "Unidad", "Cantidad"]]
        for _, row in df_agrupado.iterrows():
            data_punto.append([Paragraph(formatear_material(row["Materiales"]), styleN),
                               row["Unidad"],
                               round(row["Cantidad"], 2)])
        tabla_punto = Table(data_punto, colWidths=[4*inch, 1*inch, 1*inch])
        tabla_punto.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.black),
            ("BACKGROUND", (0,0), (-1,0), colors.darkgreen),
            ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
            ("ALIGN", (1,1), (-1,-1), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("FONTSIZE", (0,0), (-1,-1), 9),
        ]))
        elems.append(tabla_punto)
        elems.append(Spacer(1, 0.2*inch))

    # 🏁 Construcción final
    doc.build(elems)
    buffer.seek(0)
    return buffer

