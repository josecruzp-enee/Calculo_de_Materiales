# -*- coding: utf-8 -*-
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from io import BytesIO
import pandas as pd

# 🔥 TU SISTEMA
from materiales.calculos.calculo_estructuras import calcular_estructuras_por_punto
from costos_precios.mano_obra_por_punto import calcular_mano_obra_proyecto

# 🔥 BASE PROFESIONAL
from exportadores.pdf_base import fondo_pagina


# ======================================================
# 🎨 ESTILO TABLA PRINCIPAL
# ======================================================
def estilo_tabla_presupuesto():
    return [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3A5F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),

        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        ("ROWBACKGROUNDS", (0, 1), (-1, -2),
         [colors.whitesmoke, colors.transparent]),

        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#D9E2F3")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),

        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]


# ======================================================
# 📄 TABLA INSTALACIÓN
# ======================================================
def generar_tabla_presupuesto(df_detalle):

    style_small = ParagraphStyle(
        name="Small",
        fontName="Helvetica",
        fontSize=8,
        leading=9
    )

    df_resumen = (
        df_detalle
        .groupby("Estructura", as_index=False)
        .agg({
            "Cantidad": "sum",
            "Precio": "first",
            "Subtotal": "sum"
        })
        .sort_values("Subtotal", ascending=False)
    )

    data = [["DESCRIPCIÓN", "P.U.", "CANT", "TOTAL"]]

    total_general = 0

    for _, r in df_resumen.iterrows():

        estructura = r["Estructura"]
        cantidad = int(r["Cantidad"])
        pu = float(r["Precio"])
        total = float(r["Subtotal"])

        descripcion = Paragraph(
            f"Instalación de estructura tipo {estructura}",
            style_small
        )

        total_general += total

        data.append([
            descripcion,
            f"L {pu:,.2f}",
            f"{cantidad}",
            f"L {total:,.2f}",
        ])

    data.append(["", "", "TOTAL", f"L {total_general:,.2f}"])

    tabla = Table(
        data,
        colWidths=[320, 80, 60, 90],
        repeatRows=1
    )

    tabla.setStyle(estilo_tabla_presupuesto())

    return tabla, total_general


# ======================================================
# 📊 RESUMEN POR PUNTO
# ======================================================
def agregar_resumen(elementos, styles, df_totales):

    elementos.append(Paragraph("RESUMEN DE PAGO POR PUNTO", styles["Title"]))
    elementos.append(Spacer(1, 16))

    data = [["Punto", "Total (L)"]]

    for _, row in df_totales.iterrows():
        data.append([row["Punto"], f"{row['TOTAL_PUNTO']:,.2f}"])

    tabla = Table(data, colWidths=[200, 150])
    tabla.setStyle(estilo_tabla_presupuesto())

    elementos.append(tabla)
    elementos.append(Spacer(1, 20))
    elementos.append(PageBreak())


# ======================================================
# 📄 DETALLE POR PUNTO
# ======================================================
def agregar_detalle(elementos, styles, df_detalle, df_totales):

    elementos.append(Paragraph("DETALLE DE EJECUCIÓN POR PUNTO", styles["Title"]))
    elementos.append(Spacer(1, 16))

    for punto in sorted(df_detalle["Punto"].unique()):

        df_p = df_detalle[df_detalle["Punto"] == punto]

        total = df_totales[df_totales["Punto"] == punto]["TOTAL_PUNTO"].values[0]

        elementos.append(Paragraph(f"<b>PUNTO: {punto}</b>", styles["Heading2"]))
        elementos.append(Spacer(1, 6))

        data = [["Estructura", "Cant", "Precio", "Subtotal"]]

        for _, row in df_p.iterrows():
            data.append([
                row["Estructura"],
                int(row["Cantidad"]),
                f"{row['Precio']:,.2f}",
                f"{row['Subtotal']:,.2f}",
            ])

        tabla = Table(data)
        tabla.setStyle(estilo_tabla_presupuesto())

        elementos.append(tabla)
        elementos.append(Spacer(1, 8))

        elementos.append(
            Paragraph(f"<b>TOTAL: L {total:,.2f}</b>", styles["Normal"])
        )

        elementos.append(Spacer(1, 14))


# ======================================================
# 💰 COTIZACIÓN FINAL
# ======================================================
def agregar_cotizacion(elementos, styles, doc, df_detalle):

    total_base = df_detalle["Subtotal"].sum()

    ingenieria = total_base * 0.15
    subtotal = total_base + ingenieria
    isv = subtotal * 0.15
    total_final = subtotal + isv

    elementos.append(PageBreak())
    elementos.append(Paragraph("COTIZACIÓN FINAL DEL PROYECTO", styles["Title"]))
    elementos.append(Spacer(1, 16))

    data = [
        ["Concepto", "Monto (L)"],
        ["Instalación", f"L {total_base:,.2f}"],
        ["Ingeniería (15%)", f"L {ingenieria:,.2f}"],
        ["Subtotal", f"L {subtotal:,.2f}"],
        ["ISV", f"L {isv:,.2f}"],
        ["TOTAL", f"L {total_final:,.2f}"],
    ]

    tabla = Table(data, colWidths=[doc.width * 0.6, doc.width * 0.4])
    tabla.setStyle(estilo_tabla_presupuesto())

    elementos.append(tabla)


# ======================================================
# 🚀 FUNCIÓN PRINCIPAL
# ======================================================
def generar_pdf_contratista(df_estructuras: pd.DataFrame):

    if df_estructuras is None or df_estructuras.empty:
        raise ValueError("df_estructuras inválido")

    df_puntos = calcular_estructuras_por_punto(df_estructuras)
    resultado = calcular_mano_obra_proyecto(df_puntos)

    df_detalle = resultado["df_detalle"]
    df_totales = resultado["df_totales"]

    buffer = BytesIO()
    styles = getSampleStyleSheet()

    # 🔥 CORRECCIÓN CLAVE DEL LOGO
    doc = SimpleDocTemplate(
        buffer,
        topMargin=100,
        leftMargin=40,
        rightMargin=40
    )

    elementos = []

    # 🔥 PRIMERA PÁGINA (IMPORTANTE)
    elementos.append(Paragraph("<b>PRESUPUESTO DE INSTALACIÓN</b>", styles["Title"]))
    elementos.append(Spacer(1, 10))

    elementos.append(
        Paragraph("Resumen económico de ejecución de estructuras", styles["Normal"])
    )
    elementos.append(Spacer(1, 16))

    tabla, total = generar_tabla_presupuesto(df_detalle)

    elementos.append(tabla)
    elementos.append(Spacer(1, 12))

    elementos.append(
        Paragraph(f"<b>TOTAL GENERAL: L {total:,.2f}</b>", styles["Heading2"])
    )

    elementos.append(PageBreak())

    # 🔥 RESTO DEL DOCUMENTO
    agregar_resumen(elementos, styles, df_totales)
    agregar_detalle(elementos, styles, df_detalle, df_totales)
    agregar_cotizacion(elementos, styles, doc, df_detalle)

    doc.build(
        elementos,
        onFirstPage=fondo_pagina,
        onLaterPages=fondo_pagina
    )

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
