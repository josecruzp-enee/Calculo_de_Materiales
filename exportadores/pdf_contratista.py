# -*- coding: utf-8 -*-
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import pandas as pd

# 🔥 TU BIBLIOTECA
from costos_precios.precios_estructura import PRECIOS_BIBLIOTECA


# ==========================================================
# GENERAR PDF CONTRATISTA
# ==========================================================
def generar_pdf_contratista(
    df_estructuras_por_punto: pd.DataFrame,
    ruta_pdf: str = "reporte_contratista.pdf"
):

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(ruta_pdf)

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

            if estructura not in PRECIOS_BIBLIOTECA:
                precio_unit = 0
            else:
                precio_unit = PRECIOS_BIBLIOTECA[estructura]

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

        if estructura in PRECIOS_BIBLIOTECA:
            total_general += PRECIOS_BIBLIOTECA[estructura] * cantidad

    elementos.append(Spacer(1, 10))
    elementos.append(
        Paragraph(
            f"<b>TOTAL GENERAL: L {total_general:,.2f}</b>",
            styles["Heading2"]
        )
    )

    doc.build(elementos)

    return ruta_pdf
