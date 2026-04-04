# -*- coding: utf-8 -*-
"""
exportadores/pdf_completo.py
PDF PROFESIONAL FINAL (CORREGIDO + ROBUSTO + PRO)
"""

import re
from io import BytesIO
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
from exportadores.precios_estructura import procesar_precios_estructura
from exportadores.pdf_reportes_simples import _tabla_estructuras_por_punto
from exportadores.pdf_anexos_costos import (
    tabla_costos_materiales_pdf,
    tabla_mano_obra_estructuras_pdf,
)

# ==========================================================
# 🔥 UTILIDAD ROBUSTA (FIX REAL)
# ==========================================================

def _sumar_costos(df):
    if df is None or df.empty:
        return 0.0

    for col in df.columns:
        nombre = str(col).lower().strip()

        if "costo" in nombre or "total" in nombre:
            df_clean = df.copy()

            # eliminar filas resumen
            for c in df_clean.columns:
                if "material" in str(c).lower():
                    df_clean = df_clean[
                        ~df_clean[c].astype(str).str.upper().str.contains(
                            "SUBTOTAL|ISV|TOTAL", na=False
                        )
                    ]

            return float(df_clean[col].fillna(0).sum())

    return 0.0


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
    elems += generar_tabla_presupuesto(doc, styles, df_estructuras)
    elems += _seccion_estructuras_global(doc, df_estructuras)
    elems += _seccion_materiales_global(doc, df_mat)
    elems += _seccion_costos_materiales(df_costos)
    elems += _seccion_mano_obra(df_mo_estructuras)
    elems += _seccion_cotizacion(doc, df_costos, df_mo_estructuras)
    elems += _seccion_estructuras_por_punto(doc, df_estructuras_por_punto)
    elems += _seccion_materiales_por_punto(doc, df_mat_por_punto)

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
        ("LINEBELOW", (0,0), (-1,0), 1.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#EAEAEA")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),

        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
        ("ALIGN", (0,0), (0,-1), "LEFT"),

        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),

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


def _seccion_estructuras_global(doc, df):
    elems = [PageBreak()]

    elems.append(Paragraph("<b>2. LISTA DE ESTRUCTURAS</b>", styles["Heading2"]))
    elems.append(Spacer(1, 0.3 * inch))

    if df is None or df.empty:
        elems.append(Paragraph("No hay estructuras.", styleN))
        return elems

    elems.append(_tabla_estructuras_por_punto("GLOBAL", df, doc.width))
    return elems


def _seccion_materiales_global(doc, df_mat):
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
            f"{float(r['Cantidad']):,.2f}",
        ])

    tabla = Table(
        data,
        colWidths=[doc.width * 0.65, doc.width * 0.15, doc.width * 0.20]
    )
    tabla.setStyle(_tabla_estilo_pro())

    elems.append(tabla)
    return elems


def _seccion_costos_materiales(df_costos):
    if df_costos is None or df_costos.empty:
        return []

    elems = [PageBreak()]
    elems.append(Paragraph("<b>4. COSTOS DE MATERIALES</b>", styles["Heading2"]))
    elems.append(Spacer(1, 0.3 * inch))

    return extender_flowables(elems, tabla_costos_materiales_pdf(df_costos))


def _seccion_mano_obra(df):
    if df is None or df.empty:
        return []

    elems = [PageBreak()]
    elems.append(Paragraph("<b>5. COSTOS DE MANO DE OBRA</b>", styles["Heading2"]))
    elems.append(Spacer(1, 0.3 * inch))

    return extender_flowables(elems, tabla_mano_obra_estructuras_pdf(df))


def _seccion_cotizacion(doc, df_costos, df_mo):

    elems = [PageBreak()]
    elems.append(Paragraph("<b>6. COTIZACIÓN DEL PROYECTO</b>", styles["Heading1"]))
    elems.append(Spacer(1, 0.5 * inch))

    total_materiales = _sumar_costos(df_costos)
    total_mo = _sumar_costos(df_mo)

    subtotal = total_materiales + total_mo

    # 🔥 desglose del 15%
    adm = subtotal * 0.04
    ing = subtotal * 0.03
    log = subtotal * 0.02
    seg = subtotal * 0.02
    enee = subtotal * 0.02
    imp = subtotal * 0.01
    otros = subtotal * 0.01

    gastos_total = adm + ing + log + seg + enee + imp + otros

    isv = (subtotal + gastos_total) * 0.15
    total = subtotal + gastos_total + isv

    data = [
        ["Concepto", "Monto (L)"],

        ["Materiales", f"{total_materiales:,.2f}"],
        ["Mano de Obra", f"{total_mo:,.2f}"],

        ["Subtotal", f"{subtotal:,.2f}"],

        ["", ""],  # separación visual

        ["Gastos Administrativos (4%)", f"{adm:,.2f}"],
        ["Ingeniería (3%)", f"{ing:,.2f}"],
        ["Logística y Transporte (2%)", f"{log:,.2f}"],
        ["Higiene y Seguridad (2%)", f"{seg:,.2f}"],
        ["Gestión y Aprobación ENEE (2%)", f"{enee:,.2f}"],
        ["Imprevistos (1%)", f"{imp:,.2f}"],
        ["Otros (1%)", f"{otros:,.2f}"],

        ["Total Gastos", f"{gastos_total:,.2f}"],

        ["ISV (15%)", f"{isv:,.2f}"],

        ["TOTAL OFERTA", f"{total:,.2f}"],
    ]

    tabla = Table(
        data,
        colWidths=[doc.width * 0.7, doc.width * 0.3]
    )

    tabla.hAlign = "CENTER"

    tabla.setStyle(TableStyle([
        # encabezado
        ("BACKGROUND", (0,0), (-1,0), colors.darkblue),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),

        # alineación
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),

        # subtotal
        ("BACKGROUND", (0,3), (-1,3), colors.HexColor("#F2F2F2")),

        # bloque de gastos
        ("BACKGROUND", (0,5), (-1,11), colors.HexColor("#FAFAFA")),

        # total gastos
        ("BACKGROUND", (0,12), (-1,12), colors.HexColor("#EFEFEF")),
        ("FONTNAME", (0,12), (-1,12), "Helvetica-Bold"),

        # total final
        ("BACKGROUND", (0,-1), (-1,-1), colors.darkblue),
        ("TEXTCOLOR", (0,-1), (-1,-1), colors.white),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ("LINEABOVE", (0,-1), (-1,-1), 1.5, colors.black),

        # padding (más presencia)
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ]))

    elems.append(tabla)
    return elems

def _seccion_estructuras_por_punto(doc, df):
    if df is None or df.empty:
        return []

    elems = [PageBreak()]
    elems.append(Paragraph("<b>7. DETALLE POR PUNTO</b>", styles["Heading2"]))
    elems.append(Spacer(1, 0.3 * inch))

    puntos = sorted(df["Punto"].unique(), key=lambda x: int(re.sub(r"\D", "", str(x)) or 0))

    for p in puntos:
        num = re.search(r"\d+", str(p)).group()
        elems.append(Paragraph(f"<b>Punto {num}</b>", styles["Heading3"]))

        df_p = df[df["Punto"] == p]
        elems.append(_tabla_estructuras_por_punto(num, df_p, doc.width))
        elems.append(Spacer(1, 0.2 * inch))

    return elems


def _seccion_materiales_por_punto(doc, df):
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
                f"{float(r['Cantidad']):,.2f}",
            ])

        tabla = Table(
            data,
            colWidths=[doc.width * 0.65, doc.width * 0.15, doc.width * 0.20]
        )
        tabla.setStyle(_tabla_estilo_pro())

        elems.append(tabla)
        elems.append(Spacer(1, 0.3 * inch))

    return elems
