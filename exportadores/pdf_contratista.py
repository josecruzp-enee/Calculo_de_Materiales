# -*- coding: utf-8 -*-
from __future__ import annotations
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

# 🔥 BASE PDF (asegúrate de subir el logo ahí)
from exportadores.pdf_base import fondo_pagina

from reportlab.lib.units import cm

def fondo_contratista(canvas, doc):

    canvas.saveState()

    # 🔥 LOGO MÁS ARRIBA SOLO AQUÍ
    x = 40
    y = doc.pagesize[1] - 40   # ⬅️ MÁS ARRIBA

    width = 120
    height = 50

    canvas.drawImage(
        "ruta/a/tu/logo.png",  # usa tu misma ruta
        x,
        y,
        width=width,
        height=height,
        preserveAspectRatio=True,
        mask='auto'
    )

    canvas.restoreState() 
# ======================================================
# 🎨 ESTILO TABLAS
# ======================================================
def estilo_tabla():
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
# 📄 PRESUPUESTO (PÁGINA 1)
# ======================================================
def tabla_presupuesto(df_detalle):

    style_small = ParagraphStyle(
        name="Small",
        fontName="Helvetica",
        fontSize=8,
        leading=9
    )

    df = (
        df_detalle
        .groupby("Estructura", as_index=False)
        .agg({"Cantidad": "sum", "Precio": "first", "Subtotal": "sum"})
        .sort_values("Subtotal", ascending=False)
    )

    data = [["DESCRIPCIÓN", "P.U.", "CANT", "TOTAL"]]
    total = 0

    for _, r in df.iterrows():
        descripcion = Paragraph(
            f"Instalación de {r['Estructura']}",
            style_small
        )

        data.append([
            descripcion,
            f"L {r['Precio']:,.2f}",
            int(r["Cantidad"]),
            f"L {r['Subtotal']:,.2f}",
        ])

        total += r["Subtotal"]

    data.append(["", "", "TOTAL", f"L {total:,.2f}"])

    tabla = Table(data, colWidths=[320, 80, 60, 90])
    tabla.setStyle(estilo_tabla())

    return tabla


# ======================================================
# 📊 RESUMEN POR PUNTO (SIN CABLE)
# ======================================================
def pagina_resumen(elementos, styles, df_totales):

    elementos.append(Paragraph("RESUMEN DE PAGO POR PUNTO", styles["Title"]))
    elementos.append(Spacer(1, 16))

    data = [["Punto", "Total (L)"]]

    total_general = 0

    for _, r in df_totales.iterrows():
        data.append([r["Punto"], f"{r['TOTAL_PUNTO']:,.2f}"])
        total_general += r["TOTAL_PUNTO"]

    data.append(["TOTAL GENERAL", f"L {total_general:,.2f}"])

    tabla = Table(data, colWidths=[200, 150])
    tabla.setStyle(estilo_tabla())

    elementos.append(tabla)
    elementos.append(PageBreak())


# ======================================================
# 💰 RESUMEN GLOBAL (ESTRUCTURAS vs CABLE)
# ======================================================
def pagina_resumen_global(elementos, styles, df_detalle):

    subtotal_estructuras = df_detalle[
        df_detalle["Punto"].notna()
    ]["Subtotal"].sum()

    subtotal_conductores = df_detalle[
        df_detalle["Punto"].isna()
    ]["Subtotal"].sum()

    total = subtotal_estructuras + subtotal_conductores

    data = [
        ["Concepto", "Monto (L)"],
        ["Subtotal estructuras", f"L {subtotal_estructuras:,.2f}"],
        ["Subtotal conductores", f"L {subtotal_conductores:,.2f}"],
        ["TOTAL GENERAL", f"L {total:,.2f}"],
    ]

    tabla = Table(data, colWidths=[250, 150])
    tabla.setStyle(estilo_tabla())

    elementos.append(tabla)

# ======================================================
# 💰 COTIZACIÓN
# ======================================================
def pagina_cotizacion(elementos, styles, doc, df_detalle):

    total_base = df_detalle["Subtotal"].sum()

    ingenieria = total_base * 0.15
    subtotal = total_base + ingenieria
    isv = subtotal * 0.15
    total_final = subtotal + isv

    elementos.append(Paragraph("COTIZACIÓN DEL PROYECTO", styles["Title"]))
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
    tabla.setStyle(estilo_tabla())

    elementos.append(tabla)
    elementos.append(PageBreak())


# ======================================================
# 📄 DETALLE POR PUNTO
# ======================================================
def pagina_detalle(elementos, styles, df_detalle, df_totales):

    elementos.append(Paragraph("DETALLE POR PUNTO", styles["Title"]))
    elementos.append(Spacer(1, 16))

    for punto in sorted(df_detalle["Punto"].dropna().unique()):

        df_p = df_detalle[df_detalle["Punto"] == punto]

        row = df_totales[df_totales["Punto"] == punto]
        total = row["TOTAL_PUNTO"].values[0] if not row.empty else 0

        data = [[f"PUNTO: {punto}", "", "", ""]]
        data.append(["Estructura", "Cant", "Precio", "Subtotal"])

        for _, r in df_p.iterrows():
            data.append([
                r["Estructura"],
                int(r["Cantidad"]),
                f"{r['Precio']:,.2f}",
                f"{r['Subtotal']:,.2f}",
            ])

        data.append([
            f"SUBTOTAL PUNTO {punto}",
            "",
            "",
            f"L {total:,.2f}"
        ])

        tabla = Table(data, colWidths=[200, 60, 80, 100])
        tabla.setStyle(estilo_tabla())

        tabla.setStyle([
            ("SPAN", (0, -1), (2, -1)),
            ("ALIGN", (0, -1), (-1, -1), "RIGHT"),
        ])

        elementos.append(tabla)
        elementos.append(Spacer(1, 14))


# ======================================================
# 🚀 FUNCIÓN PRINCIPAL
# ======================================================
def generar_pdf_contratista(entrada):

    # 🔥 SOPORTE FLEXIBLE
    if isinstance(entrada, pd.DataFrame):
        df_estructuras = entrada
        df_cables = None
    else:
        df_estructuras = getattr(entrada, "df_estructuras", None)
        df_cables = getattr(entrada, "df_cables", None)

    if df_estructuras is None:
        raise ValueError("No hay estructuras para generar el PDF")

    # 🔧 CÁLCULO
    df_puntos = calcular_estructuras_por_punto(df_estructuras)

    resultado = calcular_mano_obra_proyecto(
        df_puntos,
        df_cables
    )

    df_detalle = resultado["df_detalle"]
    df_totales = resultado["df_totales"]

    # 📄 PDF
    buffer = BytesIO()
    styles = getSampleStyleSheet()

    doc = SimpleDocTemplate(
        buffer,
        topMargin=10,  # 🔥 LOGO MÁS ARRIBA
        leftMargin=40,
        rightMargin=40
    )

    elementos = []

    # Página 1
    elementos.append(Paragraph("PRESUPUESTO DE INSTALACIÓN", styles["Title"]))
    elementos.append(Spacer(1, 16))
    elementos.append(tabla_presupuesto(df_detalle))
    elementos.append(PageBreak())

    # Página 2
    pagina_resumen(elementos, styles, df_totales)

    # Página 3 🔥
    pagina_resumen_global(elementos, styles, df_detalle)

    # Página 4
    pagina_cotizacion(elementos, styles, doc, df_detalle)

    # Página 5+
    pagina_detalle(elementos, styles, df_detalle, df_totales)

    doc.build(
        elementos,
        onFirstPage=fondo_contratista,
        onLaterPages=fondo_contratista,
    )

  
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
