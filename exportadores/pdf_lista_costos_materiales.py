# -*- coding: utf-8 -*-
# pdf_lista_costos_materiales.py
from __future__ import annotations

from io import BytesIO
import pandas as pd

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet


# =========================================================
# PDF LISTA DE MATERIALES
# =========================================================
def generar_pdf_lista_materiales(df: pd.DataFrame, nombre_proyecto: str = "Proyecto") -> bytes:

    if df is None or df.empty:
        raise ValueError("No hay datos para generar PDF")

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    styles = getSampleStyleSheet()
    elementos = []

    # =====================================================
    # TÍTULO
    # =====================================================
    elementos.append(Paragraph(f"<b>LISTA DE MATERIALES</b>", styles["Title"]))
    elementos.append(Paragraph(f"Proyecto: {nombre_proyecto}", styles["Normal"]))
    elementos.append(Spacer(1, 10))

    # =====================================================
    # TABLA
    # =====================================================
    data = [["Material", "Unidad", "Cantidad", "P.U.", "Total"]]

    total_general = 0

    for _, row in df.iterrows():
        material = str(row["Materiales"])
        unidad = str(row["Unidad"])
        cantidad = float(row["Cantidad"])
        pu = float(row["Costo Unitario"])
        total = float(row["Costo Total"])

        total_general += total

        data.append([
            material,
            unidad,
            f"{cantidad:,.2f}",
            f"L {pu:,.2f}",
            f"L {total:,.2f}",
        ])

    # =====================================================
    # TOTAL FINAL
    # =====================================================
    data.append(["", "", "", "<b>TOTAL</b>", f"<b>L {total_general:,.2f}</b>"])

    tabla = Table(data, colWidths=[220, 60, 80, 80, 90])

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),

        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),

        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),

        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

        ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))

    elementos.append(tabla)

    # =====================================================
    # BUILD
    # =====================================================
    doc.build(elementos)

    pdf = buffer.getvalue()
    buffer.close()

    return pdf
