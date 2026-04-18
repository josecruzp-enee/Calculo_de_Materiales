# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors


# =========================================================
# HELPERS
# =========================================================
def _fmt(valor: float) -> str:
    return f"L {valor:,.2f}"


# =========================================================
# COTIZACIÓN FINAL (ROBUSTA + DEBUG)
# =========================================================
def generar_seccion_cotizacion_final(doc, styles, df_precios):

    from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors

    elems = []

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    if df_precios is None or df_precios.empty:
        elems.append(Paragraph("SIN DATOS PARA COTIZACIÓN", styles["Normal"]))
        return elems

    # =====================================================
    # TOTAL BASE
    # =====================================================
    if "Subtotal" in df_precios.columns:
        total_base = float(df_precios["Subtotal"].sum())
    else:
        total_base = float(df_precios["Precio Total"].sum())

    # =====================================================
    # GASTOS DE INGENIERÍA
    # =====================================================
    ingenieria = total_base * 0.15

    subtotal = total_base + ingenieria
    isv = subtotal * 0.15
    total_final = subtotal + isv

    # =====================================================
    # TÍTULO
    # =====================================================
    elems.append(Paragraph("<b>COTIZACIÓN DEL PROYECTO</b>", styles["Heading1"]))
    elems.append(Spacer(1, 12))

    # =====================================================
    # TABLA
    # =====================================================
    data = [
        ["Concepto", "Monto (L)"],
        ["Suministro e instalación", f"L {total_base:,.2f}"],
        ["Gastos de Ingeniería (15%)", f"L {ingenieria:,.2f}"],
        ["SUBTOTAL", f"L {subtotal:,.2f}"],
        ["ISV (15%)", f"L {isv:,.2f}"],
        ["TOTAL PROYECTO", f"L {total_final:,.2f}"],
    ]

    tabla = Table(data, colWidths=[doc.width * 0.7, doc.width * 0.3])

    tabla.setStyle(TableStyle([

        # HEADER
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

        # ALIGN
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),

        # TOTAL FINAL
        ("BACKGROUND", (0, -1), (-1, -1), colors.darkblue),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),

        # GRID
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),

    ]))

    elems.append(tabla)

    return elems
