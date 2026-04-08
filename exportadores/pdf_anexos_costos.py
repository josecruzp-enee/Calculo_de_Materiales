# -*- coding: utf-8 -*-
"""
exportadores/pdf_anexos_costos.py

Anexos de costos:
A - Materiales
B - Costos por estructura (desglosado)
C - Costos por punto
"""

import re
import pandas as pd
from xml.sax.saxutils import escape
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

from exportadores.pdf_base import styles, styleN, formatear_material


# ==========================================================
# UTIL
# ==========================================================
def _money(v):
    if v is None or pd.isna(v):
        return ""
    return f"L {float(v):,.2f}"


# ==========================================================
# ANEXO A: COSTOS DE MATERIALES
# ==========================================================
def tabla_costos_materiales_pdf(df_costos: pd.DataFrame):

    titulo = Paragraph("ANEXO A – Costos de Materiales", styles["Heading2"])

    if df_costos is None or df_costos.empty:
        return [titulo, Paragraph("No hay datos disponibles.", styles["Normal"])]

    df = df_costos.copy()
    df.columns = [str(c).strip() for c in df.columns]

    df["Cantidad"] = pd.to_numeric(df.get("Cantidad", 0), errors="coerce").fillna(0)
    df["Precio Unitario"] = pd.to_numeric(df.get("Precio Unitario", 0), errors="coerce")
    df["Costo"] = pd.to_numeric(df.get("Costo", 0), errors="coerce")

    subtotal = df["Costo"].sum()
    iva = subtotal * 0.15
    total = subtotal + iva

    data = [["Material", "Unidad", "Cantidad", "P.U.", "Costo"]]

    for _, r in df.iterrows():
        data.append([
            Paragraph(formatear_material(str(r.get("Materiales", ""))), styleN),
            escape(str(r.get("Unidad", ""))),
            f"{r['Cantidad']:,.2f}",
            _money(r["Precio Unitario"]),
            _money(r["Costo"]),
        ])

    data.append(["", "", "", "SUBTOTAL", _money(subtotal)])
    data.append(["", "", "", "ISV 15%", _money(iva)])
    data.append(["", "", "", "TOTAL", _money(total)])

    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
    ]))

    return [titulo, Spacer(1, 8), t]


# ==========================================================
# ANEXO B: COSTOS POR ESTRUCTURA (NUEVO MODELO)
# ==========================================================
def tabla_costos_estructuras_pdf(df_costos_estructuras: pd.DataFrame):

    titulo = Paragraph("ANEXO B – Costos por Estructura", styles["Heading2"])

    if df_costos_estructuras is None or df_costos_estructuras.empty:
        return [titulo, Paragraph("No hay datos disponibles.", styles["Normal"])]

    df = df_costos_estructuras.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # -----------------------------------------------------
    # NORMALIZACIÓN
    # -----------------------------------------------------
    if "codigodeestructura" not in df.columns:
        raise ValueError("Falta codigodeestructura")

    df["Cantidad"] = pd.to_numeric(df.get("Cantidad", 0), errors="coerce").fillna(0)

    # 🔥 NUEVAS COLUMNAS ESPERADAS
    for col in [
        "Costo Material",
        "Costo Operativo",
        "Costo Unitario",
        "Precio Unitario"
    ]:
        if col not in df.columns:
            df[col] = 0.0

    # -----------------------------------------------------
    # TABLA
    # -----------------------------------------------------
    data = [[
        "Estructura",
        "Cant",
        "Material",
        "Operativo",
        "Costo",
        "Precio"
    ]]

    total_costo = 0
    total_precio = 0

    for _, r in df.iterrows():

        cod = str(r["codigodeestructura"])
        cant = int(r["Cantidad"])

        mat = float(r["Costo Material"])
        op = float(r["Costo Operativo"])
        costo = float(r["Costo Unitario"])
        precio = float(r["Precio Unitario"])

        total_costo += costo * cant
        total_precio += precio * cant

        data.append([
            Paragraph(escape(cod), styleN),
            f"{cant}",
            _money(mat),
            _money(op),
            _money(costo),
            _money(precio),
        ])

    # Totales
    data.append(["", "", "", "TOTAL COSTO", _money(total_costo), ""])
    data.append(["", "", "", "TOTAL PRECIO", "", _money(total_precio)])

    t = Table(
        data,
        repeatRows=1,
        colWidths=[1.2*inch, 0.7*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch]
    )

    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("ALIGN", (1, 1), (1, -1), "CENTER"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))

    return [titulo, Spacer(1, 8), t]


# ==========================================================
# ANEXO C: COSTOS POR PUNTO
# ==========================================================
def tabla_costos_por_punto_pdf(df_detalle: pd.DataFrame):

    titulo = Paragraph("ANEXO C – Costos por Punto", styles["Heading2"])

    if df_detalle is None or df_detalle.empty:
        return [titulo, Paragraph("No hay datos disponibles.", styles["Normal"])]

    elems = [titulo, Spacer(1, 8)]

    df = df_detalle.copy()
    df.columns = [str(c).strip() for c in df.columns]

    puntos = sorted(df["Punto"].unique())

    for p in puntos:

        elems.append(Paragraph(f"<b>Punto {p}</b>", styles["Heading3"]))

        df_p = df[df["Punto"] == p]

        subtotal_costo = df_p["Subtotal Costo"].sum()
        subtotal_precio = df_p["Subtotal Precio"].sum()

        data = [
            ["Concepto", "Monto"],
            ["Costo", _money(subtotal_costo)],
            ["Precio", _money(subtotal_precio)],
        ]

        t = Table(data, colWidths=[3*inch, 2*inch])
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ]))

        elems.append(t)
        elems.append(Spacer(1, 8))

    return elems
