# -*- coding: utf-8 -*-
from __future__ import annotations

from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from exportadores.pdf_base import estilo_tabla


# =========================================================
# HELPERS VISUALES
# =========================================================
def _agregar_notas(elems, styles):

    elems.append(Spacer(1, 12))

    elems.append(Paragraph("<b>Notas:</b>", styles["Normal"]))
    elems.append(Spacer(1, 4))

    elems.append(Paragraph(
        "- Los precios incluyen el suministro e instalación de los materiales y equipos descritos en el presente documento.",
        styles["Normal"]
    ))

    elems.append(Paragraph(
        "- La gestión de permisos ante ENEE está incluida dentro del alcance del proyecto.",
        styles["Normal"]
    ))

    elems.append(Paragraph(
        "- La presente oferta tiene una validez de 30 días calendario a partir de la fecha de emisión.",
        styles["Normal"]
    ))


def _estilo_cotizacion(tabla):

    tabla.setStyle(TableStyle([

        # 🔹 SUBTOTAL (fila -3)
        ("BACKGROUND", (0, -3), (-1, -3), colors.HexColor("#D9E1F2")),
        ("FONTNAME", (0, -3), (-1, -3), "Helvetica-Bold"),

        # 🔹 ISV (fila -2)
        ("BACKGROUND", (0, -2), (-1, -2), colors.whitesmoke),

        # 🔹 TOTAL FINAL (fila -1)
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 9),
        ("TOPPADDING", (0, -1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 6),

    ]))


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================
def generar_seccion_cotizacion_final(doc, styles, df_precios):

    elems = []

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    if df_precios is None or df_precios.empty:
        elems.append(Paragraph("SIN DATOS PARA COTIZACIÓN", styles["Normal"]))
        return elems

    # =====================================================
    # TÍTULO CENTRADO
    # =====================================================
    styleTitulo = styles["Heading1"].clone("titulo_cotizacion")
    styleTitulo.alignment = TA_CENTER

    elems.append(Paragraph("COTIZACIÓN DEL PROYECTO", styleTitulo))
    elems.append(Spacer(1, 10))

    # =====================================================
    # BASE
    # =====================================================
    if "Subtotal" in df_precios.columns:
        total_base = float(df_precios["Subtotal"].sum())
    else:
        total_base = float(df_precios["Precio Total"].sum())

    # =====================================================
    # CÁLCULOS
    # =====================================================
    ingenieria = 25000
    subtotal = total_base + ingenieria
    total_final = subtotal

    # =====================================================
    # DATA
    # =====================================================
    data = [
        ["Concepto", "Monto (L)"],
        ["Suministro e instalación", f"L {total_base:,.2f}"],
        ["Gastos de Ingeniería (15%)", f"L {ingenieria:,.2f}"],
        ["TOTAL PROYECTO", f"L {total_final:,.2f}"],
    ]

    # =====================================================
    # TABLA
    # =====================================================
    tabla = Table(
        data,
        colWidths=[doc.width * 0.7, doc.width * 0.3],
        repeatRows=1
    )

    # 🔥 ESTILO GLOBAL
    tabla.setStyle(estilo_tabla())

    # 🔥 AJUSTE LOCAL
    _estilo_cotizacion(tabla)

    elems.append(tabla)

    # =====================================================
    # NOTAS
    # =====================================================
    _agregar_notas(elems, styles)

    return elems
