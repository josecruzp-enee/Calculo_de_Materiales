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
            return float("inf")
    return sorted(lista, key=clave)

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

    # Agrupar materiales si vienen repetidos
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

    # Si hay materiales adicionales, los añadimos al final
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


def generar_pdf_estructuras_global(df_estructuras, nombre_proy):
    """Genera el PDF con el resumen global de estructuras (sin separar por punto)."""
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    # --- Plantilla con fondo ---
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="con_fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = []
    elems.append(Paragraph(f"<b>Resumen de Estructuras - Proyecto: {nombre_proy}</b>", styles["Title"]))
    elems.append(Spacer(1, 12))

    # --- Validar DataFrame ---
    if df_estructuras is None or df_estructuras.empty:
        elems.append(Paragraph("No hay estructuras para mostrar.", styleN))
        doc.build(elems)
        buffer.seek(0)
        return buffer

    # --- Crear tabla ---
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

    # --- Generar documento ---
    doc.build(elems)
    buffer.seek(0)
    return buffer



def generar_pdf_estructuras_por_punto(df_por_punto, nombre_proy):
    """PDF de estructuras agrupadas por punto (ordenadas y formateadas)."""
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    # === Configurar plantilla con fondo ===
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="con_fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = []
    elems.append(Paragraph(f"<b>Estructuras por Punto - Proyecto: {nombre_proy}</b>", styles["Title"]))
    elems.append(Spacer(1, 12))

    # === Encabezado de tabla ===
    data = [["Estructura", "Descripción", "Cantidad"]]

    # Detectar columnas reales
    col_codigo = "codigodeestructura" if "codigodeestructura" in df_por_punto.columns else "Materiales"
    col_desc = "Descripcion" if "Descripcion" in df_por_punto.columns else "Materiales"

    # Ordenar los puntos numéricamente
    puntos = sorted(
        df_por_punto["Punto"].unique(),
        key=lambda x: int(re.search(r'\d+', str(x)).group()) if re.search(r'\d+', str(x)) else 0
    )

    # === Agregar datos por punto ===
    for p in puntos:
        data.append([f"Punto {p}", "", ""])  # Fila separadora de punto
        df_p = df_por_punto[df_por_punto["Punto"] == p]
        for _, row in df_p.iterrows():
            data.append([
                str(row.get(col_codigo, "")),
                str(row.get(col_desc, "")).capitalize(),
                f"{row.get('Cantidad', 0):.0f}"
            ])

    # === Crear tabla ===
    tabla = Table(data, colWidths=[1.5 * inch, 4 * inch, 1 * inch])

    estilos = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 1), (2, -1), "CENTER"),  # Centra cantidades
    ]

    # === Dar formato a las filas de título de punto ===
    row_idx = 1
    for p in puntos:
        estilos += [
            ("SPAN", (0, row_idx), (-1, row_idx)),
            ("BACKGROUND", (0, row_idx), (-1, row_idx), colors.lightblue),
            ("TEXTCOLOR", (0, row_idx), (-1, row_idx), colors.black),
            ("ALIGN", (0, row_idx), (-1, row_idx), "CENTER"),
            ("FONTNAME", (0, row_idx), (-1, row_idx), "Helvetica-Bold")
        ]
        # Saltar la fila del punto + cantidad de estructuras
        row_idx += 1 + len(df_por_punto[df_por_punto["Punto"] == p])

    tabla.setStyle(TableStyle(estilos))
    elems.append(tabla)

    doc.build(elems)
    buffer.seek(0)
    return buffer



def agregar_tabla_materiales_adicionales(elems, datos_proyecto):
    """
    Agrega una tabla de materiales adicionales (si existen) al PDF.
    Retorna la lista 'elems' actualizada.
    """
    df_extra = datos_proyecto.get("materiales_extra")
    if df_extra is None or df_extra.empty:
        return elems  # No hay materiales adicionales

    # --- Separador visual ---
    elems.append(PageBreak())
    elems.append(Paragraph("<b>Materiales Adicionales</b>", styles["Heading2"]))
    elems.append(Spacer(1, 12))

    # --- Construir tabla ---
    data_extra = [["Material", "Unidad", "Cantidad"]]
    df_extra = df_extra.copy()

    for _, row in df_extra.iterrows():
        material = str(row.get("Materiales", "")).strip().title()
        unidad = str(row.get("Unidad", "")).strip()
        cantidad = round(float(row.get("Cantidad", 0)), 2)

        data_extra.append([
            Paragraph(material, styleN),
            unidad,
            f"{cantidad:.2f}"
        ])

    tabla_extra = Table(data_extra, colWidths=[4 * inch, 1 * inch, 1 * inch])
    tabla_extra.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkorange),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))

    elems.append(tabla_extra)
    elems.append(Spacer(1, 0.2 * inch))
    return elems



def generar_pdf_completo(df_mat, df_estructuras, df_estructuras_por_punto, df_materiales_por_punto, datos_proyecto):
    """Informe completo (portada, materiales, estructuras, materiales por punto y adicionales)."""
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="con_fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])
    elems = []

    # 1️⃣ Portada
    elems += hoja_info_proyecto(datos_proyecto)

    # 2️⃣ Resumen de materiales globales
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

    # 3️⃣ Estructuras por punto
    elems.append(Paragraph("<b>Estructuras por Punto</b>", styles["Heading2"]))
    elems.append(Spacer(1, 12))

    data_est_p = [["Estructura", "Descripción", "Cantidad"]]
    puntos_est = df_estructuras_por_punto["Punto"].unique()
    for p in puntos_est:
        data_est_p.append([f"Punto {p}", "", ""])
        df_p = df_estructuras_por_punto[df_estructuras_por_punto["Punto"] == p]
        for _, row in df_p.iterrows():
            data_est_p.append([
                str(row.get("codigodeestructura", "")),
                str(row.get("Descripcion", "")).capitalize(),
                str(row.get("Cantidad", ""))
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
    for p in puntos_est:
        estilos += [
            ("SPAN", (0,row_idx), (-1,row_idx)),
            ("BACKGROUND", (0,row_idx), (-1,row_idx), colors.lightblue),
            ("ALIGN", (0,row_idx), (-1,row_idx), "CENTER"),
            ("FONTNAME", (0,row_idx), (-1,row_idx), "Helvetica-Bold")
        ]
        row_idx += 1 + len(df_estructuras_por_punto[df_estructuras_por_punto["Punto"] == p])

    tabla_est_p.setStyle(TableStyle(estilos))
    elems.append(tabla_est_p)
    elems.append(PageBreak())

    # 4️⃣ Resumen de estructuras globales
    elems.append(Paragraph("<b>Resumen de Estructuras</b>", styles["Heading2"]))
    elems.append(Spacer(1, 12))

    data_est = [["Estructura", "Descripción", "Cantidad"]]
    for _, row in df_estructuras.iterrows():
        data_est.append([
            str(row.get("codigodeestructura", "")),
            str(row.get("Descripcion", "")).capitalize(),
            str(row.get("Cantidad", ""))
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

    puntos_mat = sorted(df_materiales_por_punto["Punto"].unique(), key=lambda x: int(re.search(r'\d+', str(x)).group()))
    for p in puntos_mat:
        elems.append(Paragraph(f"<b>Punto {p}</b>", styles["Heading2"]))
        df_p = df_materiales_por_punto[df_materiales_por_punto["Punto"] == p]
        df_agrupado = df_p.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

        data_punto = [["Material", "Unidad", "Cantidad"]]
        for _, row in df_agrupado.iterrows():
            data_punto.append([
                Paragraph(formatear_material(row["Materiales"]), styleN),
                row["Unidad"],
                f"{round(row['Cantidad'], 2):.2f}"
            ])

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

    # 6️⃣ Materiales adicionales (si existen)
    elems = agregar_tabla_materiales_adicionales(elems, datos_proyecto)

    doc.build(elems)
    buffer.seek(0)
    return buffer


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
        elems.append(Paragraph(f"<b>{p}</b>", styles["Heading2"]))
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













