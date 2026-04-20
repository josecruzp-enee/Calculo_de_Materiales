# -*- coding: utf-8 -*-
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
import pandas as pd


def generar_pdf_contratista(df_detalle, df_totales):

    # ======================================================
    # PDF
    # ======================================================
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buffer)

    elementos = []

    elementos.append(Paragraph("CUADRO DE PAGO POR PUNTO", styles["Title"]))
    elementos.append(Spacer(1, 10))

    # ======================================================
    # POR PUNTO
    # ======================================================
    for punto in sorted(df_detalle["Punto"].unique()):

        df_p = df_detalle[df_detalle["Punto"] == punto]
        total_punto = df_totales[df_totales["Punto"] == punto]["TOTAL_PUNTO"].values[0]

        elementos.append(Paragraph(f"<b>PUNTO: {punto}</b>", styles["Heading2"]))
        elementos.append(Spacer(1, 6))

        # =========================
        # TABLA
        # =========================
        data = [["Estructura", "Cant", "Precio", "Subtotal"]]

        for _, row in df_p.iterrows():
            data.append([
                row["Estructura"],
                int(row["Cantidad"]),
                f"L {row['Precio']:,.2f}",
                f"L {row['Subtotal']:,.2f}",
            ])

        tabla = Table(data)

        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ]))

        elementos.append(tabla)
        elementos.append(Spacer(1, 6))

        # =========================
        # TOTAL POR PUNTO
        # =========================
        elementos.append(
            Paragraph(
                f"<b>TOTAL PUNTO: L {total_punto:,.2f}</b>",
                styles["Normal"]
            )
        )

        elementos.append(Spacer(1, 12))

    # ======================================================
    # TOTAL GENERAL
    # ======================================================
    total_general = df_totales["TOTAL_PUNTO"].sum()

    elementos.append(Spacer(1, 10))
    elementos.append(
        Paragraph(
            f"<b>TOTAL GENERAL: L {total_general:,.2f}</b>",
            styles["Heading2"]
        )
    )

    # ======================================================
    # BUILD
    # ======================================================
    doc.build(elementos)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
