# -*- coding: utf-8 -*-
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
import pandas as pd

# 🔥 TODO encapsulado aquí
from materiales.calculos.calculo_estructuras import calcular_estructuras_por_punto
from costos_precios.mano_obra_por_punto import calcular_mano_obra_proyecto


def generar_pdf_contratista(df_estructuras: pd.DataFrame):

    # ======================================================
    # VALIDACIÓN BÁSICA
    # ======================================================
    if df_estructuras is None or not isinstance(df_estructuras, pd.DataFrame) or df_estructuras.empty:
        raise ValueError("df_estructuras inválido para generar PDF contratista")

    # ======================================================
    # 🔧 CÁLCULO (ENCAPSULADO)
    # ======================================================
    df_puntos = calcular_estructuras_por_punto(df_estructuras)

    resultado = calcular_mano_obra_proyecto(df_puntos)

    df_detalle = resultado["df_detalle"]
    df_totales = resultado["df_totales"]

    # ======================================================
    # 📄 PDF
    # ======================================================
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buffer)

    elementos = []

    # ======================================================
    # TÍTULO
    # ======================================================
    elementos.append(Paragraph("CUADRO DE PAGO POR PUNTO", styles["Title"]))
    elementos.append(Spacer(1, 12))

    # ======================================================
    # POR PUNTO
    # ======================================================
    for punto in sorted(df_detalle["Punto"].unique()):

        df_p = df_detalle[df_detalle["Punto"] == punto]

        total_row = df_totales[df_totales["Punto"] == punto]
        total_punto = total_row["TOTAL_PUNTO"].values[0] if not total_row.empty else 0

        elementos.append(Paragraph(f"<b>PUNTO: {punto}</b>", styles["Heading2"]))
        elementos.append(Spacer(1, 6))

        # =========================
        # TABLA
        # =========================
        data = [["Estructura", "Cantidad", "Precio (L)", "Subtotal (L)"]]

        for _, row in df_p.iterrows():
            data.append([
                row["Estructura"],
                int(row["Cantidad"]),
                f"{row['Precio']:,.2f}",
                f"{row['Subtotal']:,.2f}",
            ])

        tabla = Table(data, colWidths=[120, 80, 100, 100])

        tabla.setStyle(TableStyle([
            # encabezado
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),

            # contenido
            ("ALIGN", (0, 1), (0, -1), "LEFT"),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),

            # bordes
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ]))

        elementos.append(tabla)
        elementos.append(Spacer(1, 8))

        # =========================
        # TOTAL POR PUNTO
        # =========================
        elementos.append(
            Paragraph(
                f"<b>TOTAL PUNTO: L {total_punto:,.2f}</b>",
                styles["Normal"]
            )
        )

        elementos.append(Spacer(1, 14))

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
