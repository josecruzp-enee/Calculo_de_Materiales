# -*- coding: utf-8 -*-
"""
exportadores/pdf_completo.py
PDF completo principal (REFactorizado).
"""

import re
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors

from exportadores.cables_pdf import tabla_cables_pdf
from exportadores.hoja_info import hoja_info_proyecto

from exportadores.pdf_base import (
    styles, styleN, styleH,
    fondo_pagina,
    salto_pagina_seguro, extender_flowables, quitar_saltos_finales,
    formatear_material,
    _calibres_por_tipo,
)

from exportadores.pdf_reportes_simples import _tabla_estructuras_por_punto
from exportadores.pdf_anexos_costos import (
    tabla_costos_materiales_pdf,
    tabla_mano_obra_estructuras_pdf,
)

# ==========================================================
# ORQUESTADOR PRINCIPAL
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
    elems += _seccion_materiales_global(df_mat)
    elems += _seccion_cables(datos_proyecto)
    elems += _seccion_estructuras_global(df_estructuras)
    elems += _seccion_estructuras_por_punto(df_estructuras_por_punto)
    elems += _seccion_materiales_por_punto(df_mat_por_punto)
    elems += _seccion_anexo_costos(df_costos)
    elems += _seccion_anexo_mano_obra(df_mo_estructuras)
    elems += _seccion_resumen_economico(df_costos, df_mo_estructuras)

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
        leftMargin=40,
        rightMargin=40,
        topMargin=120,
        bottomMargin=40
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


def _seccion_materiales_global(df_mat):
    elems = []
    salto_pagina_seguro(elems)

    elems.append(Paragraph("<b>Resumen de Materiales</b>", styles["Heading2"]))

    if df_mat is None or df_mat.empty:
        elems.append(Paragraph("No se encontraron materiales.", styleN))
        return elems

    df = df_mat.copy()
    df.columns = [str(c).strip() for c in df.columns]

    df_agr = df.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

    data = [["Material", "Unidad", "Cantidad"]]

    for _, r in df_agr.iterrows():
        data.append([
            Paragraph(formatear_material(r["Materiales"]), styleN),
            escape(str(r["Unidad"])),
            f"{float(r['Cantidad']):.2f}",
        ])

    tabla = Table(data, colWidths=[4 * inch, 1 * inch, 1 * inch])

    tabla.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
    ]))

    elems.append(tabla)
    return elems


def _seccion_cables(datos_proyecto):
    return extender_flowables([], tabla_cables_pdf(datos_proyecto))


def _seccion_estructuras_global(df_estructuras):
    elems = []
    salto_pagina_seguro(elems)

    elems.append(Paragraph("<b>Resumen de Estructuras</b>", styles["Heading2"]))

    if df_estructuras is None or df_estructuras.empty:
        elems.append(Paragraph("No se encontraron estructuras.", styleN))
        return elems

    elems.append(
        _tabla_estructuras_por_punto("GLOBAL", df_estructuras, letter[0])
    )

    return elems


def _seccion_estructuras_por_punto(df):
    elems = []

    if df is None or df.empty:
        return elems

    salto_pagina_seguro(elems)
    elems.append(Paragraph("<b>Estructuras por Punto</b>", styles["Heading2"]))

    df.columns = [str(c).strip() for c in df.columns]

    puntos = sorted(df["Punto"].unique(), key=lambda x: int(re.sub(r"\D", "", str(x)) or 0))

    for p in puntos:
        num = re.search(r"\d+", str(p)).group()

        elems.append(Paragraph(f"<b>Punto {num}</b>", styles["Heading3"]))

        df_p = df[df["Punto"] == p]

        elems.append(_tabla_estructuras_por_punto(num, df_p, letter[0]))
        elems.append(Spacer(1, 0.2 * inch))

    return elems


def _seccion_materiales_por_punto(df):
    elems = []

    if df is None or df.empty:
        return elems

    salto_pagina_seguro(elems)
    elems.append(Paragraph("<b>Materiales por Punto</b>", styles["Heading2"]))

    df.columns = [str(c).strip() for c in df.columns]

    for p in sorted(df["Punto"].unique()):
        elems.append(Paragraph(f"<b>Punto {p}</b>", styles["Heading3"]))

        df_p = df[df["Punto"] == p]

        df_agr = df_p.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

        data = [["Material", "Unidad", "Cantidad"]]

        for _, r in df_agr.iterrows():
            data.append([
                Paragraph(formatear_material(r["Materiales"]), styleN),
                r["Unidad"],
                f"{float(r['Cantidad']):.2f}",
            ])

        tabla = Table(data, colWidths=[4 * inch, 1 * inch, 1 * inch])
        elems.append(tabla)

    return elems


def _seccion_anexo_costos(df_costos):
    if df_costos is None or df_costos.empty:
        return []

    elems = []
    salto_pagina_seguro(elems)

    return extender_flowables(elems, tabla_costos_materiales_pdf(df_costos))


def _seccion_anexo_mano_obra(df):
    if df is None or df.empty:
        return []

    elems = []
    salto_pagina_seguro(elems)

    return extender_flowables(elems, tabla_mano_obra_estructuras_pdf(df))


def _seccion_resumen_economico(df_costos, df_mo):
    if df_costos is None or df_mo is None:
        return []

    elems = []
    salto_pagina_seguro(elems)

    elems.append(Paragraph("<b>Resumen Económico del Proyecto</b>", styles["Heading2"]))

    total_materiales = float(df_costos["Total"].sum()) if "Total" in df_costos else 0
    total_mo = float(df_mo["MO Total"].sum()) if "MO Total" in df_mo else 0

    equipos = total_mo * 0.10
    directos = total_materiales + total_mo + equipos

    ingenieria = directos * 0.07
    administracion = directos * 0.05
    imprevistos = directos * 0.04

    indirectos = ingenieria + administracion + imprevistos
    utilidad = (directos + indirectos) * 0.15

    subtotal = directos + indirectos + utilidad
    isv = subtotal * 0.15
    total_final = subtotal + isv

    data = [
        ["Concepto", "Monto (L)"],
        ["Materiales", f"{total_materiales:,.2f}"],
        ["Mano de Obra", f"{total_mo:,.2f}"],
        ["Equipos", f"{equipos:,.2f}"],
        ["Directos", f"{directos:,.2f}"],
        ["Indirectos", f"{indirectos:,.2f}"],
        ["Utilidad", f"{utilidad:,.2f}"],
        ["Subtotal", f"{subtotal:,.2f}"],
        ["ISV", f"{isv:,.2f}"],
        ["TOTAL", f"{total_final:,.2f}"],
    ]

    tabla = Table(data, colWidths=[4 * inch, 2 * inch])

    tabla.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.darkblue),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
        ("BACKGROUND", (0,-1), (-1,-1), colors.lightgrey),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
    ]))

    elems.append(tabla)

    return elems
