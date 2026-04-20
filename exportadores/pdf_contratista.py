# -*- coding: utf-8 -*-
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
import pandas as pd

# 🔥 TU SISTEMA
from materiales.calculos.calculo_estructuras import calcular_estructuras_por_punto
from costos_precios.mano_obra_por_punto import calcular_mano_obra_proyecto

# 🔥 BASE PROFESIONAL
from exportadores.pdf_base import estilo_tabla, fondo_pagina


# ======================================================
# 📊 RESUMEN (PÁGINA 1)
# ======================================================
def _agregar_resumen(elementos, styles, df_totales):

    elementos.append(Paragraph("RESUMEN DE PAGO POR PUNTO", styles["Title"]))
    elementos.append(Spacer(1, 12))

    data = [["Punto", "Total (L)"]]

    for _, row in df_totales.iterrows():
        data.append([
            row["Punto"],
            f"{row['TOTAL_PUNTO']:,.2f}"
        ])

    tabla = Table(data, colWidths=[200, 150])
    tabla.setStyle(estilo_tabla())

    elementos.append(tabla)
    elementos.append(Spacer(1, 12))

    total_general = df_totales["TOTAL_PUNTO"].sum()

    elementos.append(
        Paragraph(f"<b>TOTAL GENERAL: L {total_general:,.2f}</b>", styles["Heading2"])
    )

    elementos.append(PageBreak())


# ======================================================
# 📄 DETALLE POR PUNTO
# ======================================================
def _agregar_detalle_puntos(elementos, styles, df_detalle, df_totales):

    elementos.append(Paragraph("CUADRO DE PAGO POR PUNTO", styles["Title"]))
    elementos.append(Spacer(1, 12))

    for punto in sorted(df_detalle["Punto"].unique()):

        df_p = df_detalle[df_detalle["Punto"] == punto]

        total_row = df_totales[df_totales["Punto"] == punto]
        total_punto = total_row["TOTAL_PUNTO"].values[0] if not total_row.empty else 0

        elementos.append(Paragraph(f"<b>PUNTO: {punto}</b>", styles["Heading2"]))
        elementos.append(Spacer(1, 6))

        data = [["Estructura", "Cantidad", "Precio (L)", "Subtotal (L)"]]

        for _, row in df_p.iterrows():
            data.append([
                row["Estructura"],
                int(row["Cantidad"]),
                f"{row['Precio']:,.2f}",
                f"{row['Subtotal']:,.2f}",
            ])

        tabla = Table(data, colWidths=[140, 80, 110, 110])
        tabla.setStyle(estilo_tabla())

        elementos.append(tabla)
        elementos.append(Spacer(1, 8))

        elementos.append(
            Paragraph(
                f"<b>TOTAL PUNTO: L {total_punto:,.2f}</b>",
                styles["Normal"]
            )
        )

        elementos.append(Spacer(1, 14))


# ======================================================
# 🧾 TOTAL GENERAL FINAL
# ======================================================
def _agregar_total_general(elementos, styles, df_totales):

    total_general = df_totales["TOTAL_PUNTO"].sum()

    elementos.append(Spacer(1, 10))
    elementos.append(
        Paragraph(
            f"<b>TOTAL GENERAL: L {total_general:,.2f}</b>",
            styles["Heading2"]
        )
    )


# ======================================================
# 🚀 FUNCIÓN PRINCIPAL
# ======================================================
def generar_pdf_contratista(df_estructuras: pd.DataFrame):

    if df_estructuras is None or df_estructuras.empty:
        raise ValueError("df_estructuras inválido")

    # 🔧 cálculo
    df_puntos = calcular_estructuras_por_punto(df_estructuras)
    resultado = calcular_mano_obra_proyecto(df_puntos)

    df_detalle = resultado["df_detalle"]
    df_totales = resultado["df_totales"]

    # 📄 PDF
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buffer)

    elementos = []

    # 🔥 modular
    _agregar_resumen(elementos, styles, df_totales)
    _agregar_detalle_puntos(elementos, styles, df_detalle, df_totales)
    _agregar_total_general(elementos, styles, df_totales)

    # 🔥 CLAVE: APLICAR MEMBRETE / LOGO
    doc.build(
        elementos,
        onFirstPage=fondo_pagina,
        onLaterPages=fondo_pagina
    )

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
