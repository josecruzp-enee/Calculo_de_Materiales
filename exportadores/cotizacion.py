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
def generar_seccion_cotizacion_final(
    doc,
    styles,
    df_precios,
):

    elems = []

    if df_precios is None or df_precios.empty:
        raise ValueError("df_precios vacío")

    # 🔥 TOTAL REAL DEL PROYECTO (BASE)
    total_base = float(df_precios["Subtotal"].sum())

    # =====================================================
    # GASTOS
    # =====================================================
    gastos_admin = total_base * 0.04
    ingenieria = total_base * 0.03
    logistica = total_base * 0.02
    seguridad = total_base * 0.02
    enee = total_base * 0.02
    imprevistos = total_base * 0.01

    total_gastos = (
        gastos_admin + ingenieria + logistica +
        seguridad + enee + imprevistos
    )

    subtotal = total_base + total_gastos
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
        ["Gastos Administrativos (4%)", f"L {gastos_admin:,.2f}"],
        ["Ingeniería (3%)", f"L {ingenieria:,.2f}"],
        ["Logística y Transporte (2%)", f"L {logistica:,.2f}"],
        ["Higiene y Seguridad (2%)", f"L {seguridad:,.2f}"],
        ["Gestión ENEE (2%)", f"L {enee:,.2f}"],
        ["Imprevistos (1%)", f"L {imprevistos:,.2f}"],
        ["TOTAL GASTOS", f"L {total_gastos:,.2f}"],
        ["SUBTOTAL", f"L {subtotal:,.2f}"],
        ["ISV (15%)", f"L {isv:,.2f}"],
        ["TOTAL PROYECTO", f"L {total_final:,.2f}"],
    ]

    tabla = Table(data, colWidths=[doc.width * 0.7, doc.width * 0.3])

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),

        ("BACKGROUND", (0, -1), (-1, -1), colors.darkblue),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),

        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elems.append(tabla)

    return elems
