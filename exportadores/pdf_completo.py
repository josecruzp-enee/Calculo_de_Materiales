# -*- coding: utf-8 -*-
"""
exportadores/pdf_completo.py
PDF PROFESIONAL FINAL (LISTO PARA CLIENTE)
"""

import re
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors

from exportadores.cables_pdf import tabla_cables_pdf
from exportadores.hoja_info import hoja_info_proyecto

from exportadores.pdf_base import (
    styles, styleN, styleH,
    fondo_pagina,
    extender_flowables, quitar_saltos_finales,
    formatear_material,
    _calibres_por_tipo,
)

from exportadores.pdf_reportes_simples import _tabla_estructuras_por_punto
from exportadores.pdf_anexos_costos import (
    tabla_costos_materiales_pdf,
    tabla_mano_obra_estructuras_pdf,
)

# ==========================================================
# ORQUESTADOR
# ==========================================================

def generar_pdf_completo(
    df_mat,
    df_estructuras,
    df_estructuras_por_punto,
    df_mat_por_punto,
    datos_proyecto,
    df_costos=None,
    df_mo_estructuras=None,
):
    buffer, doc, elems = _crear_documento(datos_proyecto)

    elems += _seccion_info(datos_proyecto, df_estructuras, df_mat)
    elems += _seccion_estructuras_global(df_estructuras)
    elems += _seccion_materiales_global(df_mat)
    elems += _seccion_costos_materiales(df_costos)
    elems += _seccion_mano_obra(df_mo_estructuras)
    elems += _seccion_cotizacion(df_costos, df_mo_estructuras)

    # DETALLE (opcional)
    elems += _seccion_estructuras_por_punto(df_estructuras_por_punto)
    elems += _seccion_materiales_por_punto(df_mat_por_punto)

    quitar_saltos_finales(elems)
    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes


# ==========================================================
# BASE DOCUMENTO
# ==========================================================

def _crear_documento(datos_proyecto):
    buffer = BytesIO()

    doc = BaseDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=60,
        rightMargin=60,
        topMargin=160,
        bottomMargin=50
    )

    doc.membrete_pdf = datos_proyecto.get("membrete_pdf", "SMART")

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)

    template = PageTemplate(
        id="fondo",
        frames=[frame],
        onPage=fondo_pagina
    )

    doc.addPageTemplates([template])

    return buffer, doc, []


# ==========================================================
# ESTILO TABLA PRO
# ==========================================================

def _tabla_estilo_pro():
    return TableStyle([
        ("LINEBELOW", (0,0), (-1,0), 1.2, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#E8E8E8")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),

        ("ALIGN", (1,1), (-1,-1), "CENTER"),

        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),

        ("ROWBACKGROUNDS", (0,1), (-1,-1),
         [colors.white, colors.HexColor("#F7F7F7")])
    ])


# ==========================================================
# SECCIONES
# ==========================================================

def _seccion_info(datos_proyecto, df_estructuras, df_mat):
    return extender_flowables(
        [],
        hoja_info_proyecto(
            datos_proyecto,
            df_estructuras,
            df_mat,
            styles=styles,
            styleN=styleN,
            styleH=styleH,
            _calibres_por_tipo=_calibres_por_tipo
        )
    )


# ----------------------------------------------------------

def _seccion_estructuras_global(df):
    elems = [PageBreak()]

    elems.append(Paragraph("<b>2. LISTA DE ESTRUCTURAS</b>", styles["Heading2"]))
    elems.append(Spacer(1, 0.3 * inch))

    if df is None or df.empty:
        elems.append(Paragraph("No hay estructuras.", styleN))
        return elems

    elems.append(_tabla_estructuras_por_punto("GLOBAL", df, letter[0]))
    elems.append(Spacer(1, 0.4 * inch))

    return elems


# ----------------------------------------------------------

def _seccion_materiales_global(df_mat):
    elems = [PageBreak()]

    elems.append(Paragraph("<b>3. LISTA DE MATERIALES</b>", styles["Heading2"]))
    elems.append(Spacer(1, 0.3 * inch))

    if df_mat is None or df_mat.empty:
        elems.append(Paragraph("No hay materiales.", styleN))
        return elems

    df_agr = df_mat.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

    data = [["Material", "Unidad", "Cantidad"]]

    for _, r in df_agr.iterrows():
        data.append([
            Paragraph(formatear_material(r["Materiales"]), styleN),
            r["Unidad"],
            f"{float(r['Cantidad']):.2f}",
        ])

    tabla = Table(data, colWidths=[3.5 * inch, 1.2 * inch, 1.2 * inch])
    tabla.setStyle(_tabla_estilo_pro())

    elems.append(tabla)
    elems.append(Spacer(1, 0.4 * inch))

    return elems


# ----------------------------------------------------------

def _seccion_costos_materiales(df_costos):
    if df_costos is None or df_costos.empty:
        return []

    elems = [PageBreak()]

    elems.append(Paragraph("<b>4. COSTOS DE MATERIALES</b>", styles["Heading2"]))
    elems.append(Spacer(1, 0.3 * inch))

    return extender_flowables(elems, tabla_costos_materiales_pdf(df_costos))


# ----------------------------------------------------------

def _seccion_mano_obra(df):
    if df is None or df.empty:
        return []

    elems = [PageBreak()]

    elems.append(Paragraph("<b>5. COSTOS DE MANO DE OBRA</b>", styles["Heading2"]))
    elems.append(Spacer(1, 0.3 * inch))

    return extender_flowables(elems, tabla_mano_obra_estructuras_pdf(df))


# ----------------------------------------------------------

def _seccion_cotizacion(df_costos, df_mo):

    if df_costos is None or df_mo is None:
        return []

    elems = [PageBreak()]

    elems.append(Paragraph("<b>6. COTIZACIÓN DEL PROYECTO</b>", styles["Heading2"]))
    elems.append(Spacer(1, 0.4 * inch))

    total_materiales = df_costos["Total"].sum()
    total_mo = df_mo["MO Total"].sum()

    subtotal = total_materiales + total_mo
    utilidad = subtotal * 0.15
    isv = (subtotal + utilidad) * 0.15
    total = subtotal + utilidad + isv

    data = [
        ["Concepto", "Monto (L)"],
        ["Materiales", f"{total_materiales:,.2f}"],
        ["Mano de Obra", f"{total_mo:,.2f}"],
        ["Subtotal", f"{subtotal:,.2f}"],
        ["Utilidad (15%)", f"{utilidad:,.2f}"],
        ["ISV (15%)", f"{isv:,.2f}"],
        ["TOTAL OFERTA", f"{total:,.2f}"],
    ]

    tabla = Table(data, colWidths=[4 * inch, 2 * inch])

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.darkblue),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("BACKGROUND", (0,-1), (-1,-1), colors.lightgrey),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
    ]))

    elems.append(tabla)

    return elems


# ----------------------------------------------------------

def _seccion_estructuras_por_punto(df):
    if df is None or df.empty:
        return []

    df = df[~df["Estructura"].str.contains("NO ENCONTRADA", na=False)]

    elems = [PageBreak()]

    elems.append(Paragraph("<b>7. DETALLE POR PUNTO</b>", styles["Heading2"]))
    elems.append(Spacer(1, 0.3 * inch))

    puntos = sorted(df["Punto"].unique(), key=lambda x: int(re.sub(r"\D", "", str(x)) or 0))

    for p in puntos:
        num = re.search(r"\d+", str(p)).group()
        elems.append(Paragraph(f"<b>Punto {num}</b>", styles["Heading3"]))

        df_p = df[df["Punto"] == p]
        elems.append(_tabla_estructuras_por_punto(num, df_p, letter[0]))
        elems.append(Spacer(1, 0.2 * inch))

    return elems


# ----------------------------------------------------------

def _seccion_materiales_por_punto(df):
    if df is None or df.empty:
        return []

    elems = [PageBreak()]

    elems.append(Paragraph("<b>8. MATERIALES POR PUNTO</b>", styles["Heading2"]))
    elems.append(Spacer(1, 0.3 * inch))

    for p in sorted(df["Punto"].unique()):
        num = re.search(r"\d+", str(p)).group()
        elems.append(Paragraph(f"<b>Punto {num}</b>", styles["Heading3"]))

        df_p = df[df["Punto"] == p]
        df_agr = df_p.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

        data = [["Material", "Unidad", "Cantidad"]]

        for _, r in df_agr.iterrows():
            data.append([
                Paragraph(formatear_material(r["Materiales"]), styleN),
                r["Unidad"],
                f"{float(r['Cantidad']):.2f}",
            ])

        tabla = Table(data, colWidths=[3.5 * inch, 1.2 * inch, 1.2 * inch])
        tabla.setStyle(_tabla_estilo_pro())

        elems.append(tabla)
        elems.append(Spacer(1, 0.3 * inch))

    return elems
