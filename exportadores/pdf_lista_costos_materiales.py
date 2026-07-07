# -*- coding: utf-8 -*-
from __future__ import annotations

from io import BytesIO
import pandas as pd

from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER


# =========================================================
# 🔧 VALIDACIÓN
# =========================================================
def _validar_df(df: pd.DataFrame):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("DataFrame inválido o vacío")

    columnas = {
        "Materiales",
        "Unidad",
        "Cantidad",
        "Costo Unitario",
        "Costo Total",
    }

    faltantes = columnas - set(df.columns)

    if faltantes:
        raise ValueError(
            f"Columnas faltantes: {list(faltantes)}. "
            f"Columnas recibidas: {list(df.columns)}"
        )


# =========================================================
# 🎨 ESTILOS
# =========================================================
def _get_styles():
    base = getSampleStyleSheet()

    styles = {
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=16,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "normal": ParagraphStyle(
            "normal",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=11,
        ),
        "header": ParagraphStyle(
            "header",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=8,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),
        "cell_left": ParagraphStyle(
            "cell_left",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=6.5,
            leading=7.5,
            alignment=TA_LEFT,
        ),
        "cell_center": ParagraphStyle(
            "cell_center",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=6.5,
            leading=7.5,
            alignment=TA_CENTER,
        ),
        "cell_right": ParagraphStyle(
            "cell_right",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=6.5,
            leading=7.5,
            alignment=TA_RIGHT,
        ),
        "cell_right_bold": ParagraphStyle(
            "cell_right_bold",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=8,
            alignment=TA_RIGHT,
        ),
    }

    return styles


# =========================================================
# 🔧 TEXTO SEGURO PARA PDF
# =========================================================
def _txt(valor) -> str:
    if pd.isna(valor):
        return ""
    return str(valor).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _money(valor) -> str:
    try:
        return f"L {float(valor):,.2f}"
    except Exception:
        return "L 0.00"


def _num(valor) -> str:
    try:
        return f"{float(valor):,.2f}"
    except Exception:
        return "0.00"


# =========================================================
# 🧾 HEADER
# =========================================================
def _build_header(elementos, styles, nombre_proyecto):
    elementos.append(Paragraph("LISTA DE MATERIALES", styles["title"]))
    elementos.append(
        Paragraph(f"<b>Proyecto:</b> {_txt(nombre_proyecto)}", styles["normal"])
    )
    elementos.append(Spacer(1, 10))


# =========================================================
# 📊 DATA TABLA
# =========================================================
def _build_data(df: pd.DataFrame, styles):

    data = [[
        Paragraph("Material", styles["header"]),
        Paragraph("Unidad", styles["header"]),
        Paragraph("Cantidad", styles["header"]),
        Paragraph("P.U.", styles["header"]),
        Paragraph("Total", styles["header"]),
    ]]

    total_general = 0.0

    for _, row in df.iterrows():
        material = _txt(row.get("Materiales", ""))
        unidad = _txt(row.get("Unidad", ""))
        cantidad = row.get("Cantidad", 0)
        pu = row.get("Costo Unitario", 0)
        total = row.get("Costo Total", 0)

        try:
            total_general += float(total)
        except Exception:
            pass

        data.append([
            Paragraph(material, styles["cell_left"]),
            Paragraph(unidad, styles["cell_center"]),
            Paragraph(_num(cantidad), styles["cell_right"]),
            Paragraph(_money(pu), styles["cell_right"]),
            Paragraph(_money(total), styles["cell_right"]),
        ])

    data.append([
        "",
        "",
        "",
        Paragraph("<b>TOTAL</b>", styles["cell_right_bold"]),
        Paragraph(f"<b>{_money(total_general)}</b>", styles["cell_right_bold"]),
    ])

    return data, total_general


# =========================================================
# 📐 TABLA
# =========================================================
def _build_table(data):

    tabla = Table(
        data,
        colWidths=[
            7.7 * cm,   # Material
            1.6 * cm,   # Unidad
            1.8 * cm,   # Cantidad
            2.2 * cm,   # P.U.
            2.5 * cm,   # Total
        ],
        repeatRows=1,
        hAlign="CENTER",
    )

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#666666")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),

        ("GRID", (0, 0), (-1, -1), 0.35, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),

        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),

        ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
        ("SPAN", (0, -1), (2, -1)),
        ("VALIGN", (0, -1), (-1, -1), "MIDDLE"),
    ]))

    return tabla


# =========================================================
# 🏗 BUILD PDF
# =========================================================
def _build_pdf(elementos):

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=1.2 * cm,
        leftMargin=1.2 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm,
    )

    doc.build(elementos)

    pdf = buffer.getvalue()
    buffer.close()

    if not pdf or len(pdf) < 100:
        raise ValueError("PDF generado vacío")

    return pdf


# =========================================================
# 🚀 MOTOR PRINCIPAL
# =========================================================
def generar_pdf_lista_materiales(
    df: pd.DataFrame,
    nombre_proyecto: str = "Proyecto"
) -> bytes:

    _validar_df(df)

    styles = _get_styles()
    elementos = []

    _build_header(elementos, styles, nombre_proyecto)

    data, _ = _build_data(df, styles)

    tabla = _build_table(data)
    elementos.append(tabla)

    return _build_pdf(elementos)
