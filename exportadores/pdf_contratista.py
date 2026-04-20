# -*- coding: utf-8 -*-
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
import pandas as pd

from costos_precios.precios_estructura import PRECIOS_BIBLIOTECA

# 🔥 AJUSTA ESTE IMPORT
from entradas.tu_archivo import calcular_estructuras_por_punto


def generar_pdf_contratista(df_estructuras: pd.DataFrame):

    # ======================================================
    # CONVERTIR A POR PUNTO
    # ======================================================
    df_estructuras_por_punto = calcular_estructuras_por_punto(df_estructuras)

    # ======================================================
    # BUFFER (CLAVE PARA ORQUESTADOR)
    # ======================================================
    buffer = BytesIO()

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buffer)

    elementos = []

    elementos.append(Paragraph("CUADRO DE PAGO POR PUNTO", styles["Title"]))
    elementos.append(Spacer(1, 10))

    # ======================================================
    # PROCESO POR PUNTO
    # ======================================================
    for punto in sorted(df_estructuras_por_punto["Punto"].unique()):

        df_p = df_estructuras_por_punto[
            df_estructuras_por_punto["Punto"] == punto
        ]

        elementos.append(Paragraph(f"<b>PUNTO: {punto}</b>", styles["Heading2"]))
        elementos.append(Spacer(1, 6))

        total_punto = 0

        for _, row in df_p.iterrows():

            estructura = row["Estructura"]
            cantidad = int(row["Cantidad"])

            precio_unit = PRECIOS_BIBLIOTECA.get(estructura, 0)

            subtotal = precio_unit * cantidad
            total_punto += subtotal

            texto = f"{estructura} ({cantidad}) .......... L {subtotal:,.2f}"
            elementos.append(Paragraph(texto, styles["Normal"]))

        elementos.append(Spacer(1, 6))

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
    total_general = 0

    for _, row in df_estructuras_por_punto.iterrows():
        estructura = row["Estructura"]
        cantidad = int(row["Cantidad"])

        total_general += PRECIOS_BIBLIOTECA.get(estructura, 0) * cantidad

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
