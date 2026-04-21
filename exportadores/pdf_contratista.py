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

from materiales.calculos.calculo_estructuras import calcular_estructuras_por_punto
from costos_precios.mano_obra_por_punto import calcular_mano_obra_proyecto
from exportadores.pdf_base import fondo_pagina


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
# 📄 PRESUPUESTO
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
        .agg({
            "Cantidad": "sum",
            "Precio": "first",
            "Subtotal": "sum"
        })
    )

    # ======================================================
    # 🔥 ORDEN JERÁRQUICO (SIN SEPARAR)
    # ======================================================
    def _orden(nombre):

        n = str(nombre).upper()

        if "TS-" in n:
            return 1  # Transformadores

        elif "PC-" in n:
            return 2  # Postes

        elif (
            "CONDUCTOR MT" in n
            or "FASES BT" in n
            or "NEUTRO" in n
            or "HILO PILOTO" in n
        ):
            return 3  # Conductores

        elif n.startswith("A-"):
            return 4  # Primarios

        elif n.startswith("B-"):
            return 5  # Secundarios

        elif "LL-" in n:
            return 6  # Luminarias

        elif n.startswith("R-"):
            return 7  # Retenidas

        elif "CA-" in n or "CS-" in n:
            return 8  # Aterrizajes

        else:
            return 9  # Otros

    df["orden"] = df["Estructura"].apply(_orden)

    # 🔥 Orden final
    df = df.sort_values(["orden", "Subtotal"], ascending=[True, False])

    # ======================================================
    # 📄 TABLA
    # ======================================================
    data = [["DESCRIPCIÓN", "P.U.", "CANT", "TOTAL"]]
    total = 0

    for _, r in df.iterrows():

        descripcion_txt = str(r["Estructura"]).upper()
        cantidad = r["Cantidad"]
        precio = r["Precio"]

        # 🔥 Limpiar texto duplicado
        texto = str(r["Estructura"]).replace("BT BT", "BT")
        texto = f"Instalación de {texto}"

        # 🔥 Aclaración técnica
        if "FASES BT" in descripcion_txt:
            texto += " (2 Fases)"

        descripcion = Paragraph(texto, style_small)

        data.append([
            descripcion,
            f"L {precio:,.2f}",
            int(cantidad),
            f"L {r['Subtotal']:,.2f}",
        ])

        total += r["Subtotal"]

    data.append(["", "", "TOTAL", f"L {total:,.2f}"])

    tabla = Table(data, colWidths=[320, 80, 60, 90])
    tabla.setStyle(estilo_tabla())

    return tabla

# ======================================================
# 📊 RESUMEN POR PUNTO
# ======================================================
def pagina_resumen(elementos, styles, df_totales):

    elementos.append(Paragraph("RESUMEN DE PAGO POR PUNTO", styles["Title"]))
    elementos.append(Spacer(1, 12))

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
# 💰 RESUMEN GLOBAL
# ======================================================
def pagina_resumen_global(elementos, styles, df_detalle):

    subtotal_estructuras = df_detalle[df_detalle["Punto"].notna()]["Subtotal"].sum()
    subtotal_conductores = df_detalle[df_detalle["Punto"].isna()]["Subtotal"].sum()

    grua = 18000
    rastra = 25000

    total_mano_obra = subtotal_estructuras + subtotal_conductores
    total_logistica = grua + rastra
    total_general = total_mano_obra + total_logistica

    data = [
        ["Concepto", "Monto (L)"],
        ["Mano de Obra (Estructuras)", f"L {subtotal_estructuras:,.2f}"],
        ["Mano de Obra (Conductores)", f"L {subtotal_conductores:,.2f}"],
        ["TOTAL MANO DE OBRA", f"L {total_mano_obra:,.2f}"],
        ["Equipo Grúa", f"L {grua:,.2f}"],
        ["Flete de Postes", f"L {rastra:,.2f}"],
        ["TOTAL LOGÍSTICA", f"L {total_logistica:,.2f}"],
        ["TOTAL GENERAL", f"L {total_general:,.2f}"],
    ]

    tabla = Table(data, colWidths=[250, 150])
    tabla.setStyle(estilo_tabla())

    # 🔥 Resaltar subtotales
    tabla.setStyle([
        ("BACKGROUND", (0, 3), (-1, 3), colors.lightgrey),
        ("BACKGROUND", (0, 6), (-1, 6), colors.lightgrey),
    ])

    elementos.append(tabla)
    elementos.append(PageBreak())


# ======================================================
# 💰 COTIZACIÓN
# ======================================================
def pagina_cotizacion(elementos, styles, doc, df_detalle):

    subtotal_estructuras = df_detalle[df_detalle["Punto"].notna()]["Subtotal"].sum()
    subtotal_conductores = df_detalle[df_detalle["Punto"].isna()]["Subtotal"].sum()

    mano_obra = subtotal_estructuras + subtotal_conductores

    grua = 18000
    rastra = 25000
    logistica = grua + rastra

    ingenieria = 25000

    subtotal = mano_obra + logistica + ingenieria
    isv = subtotal * 0.15
    total_final = subtotal + isv

    elementos.append(Paragraph("COTIZACIÓN DEL PROYECTO", styles["Title"]))
    elementos.append(Spacer(1, 16))

    data = [
        ["Concepto", "Monto (L)"],
        ["Mano de Obra", f"L {mano_obra:,.2f}"],
        ["Logística", f"L {logistica:,.2f}"],
        ["Ingeniería", f"L {ingenieria:,.2f}"],
        ["Subtotal", f"L {subtotal:,.2f}"],
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
        total = df_totales[df_totales["Punto"] == punto]["TOTAL_PUNTO"].values[0]

        data = [[f"PUNTO: {punto}", "", "", ""]]
        data.append(["Estructura", "Cant", "Precio", "Subtotal"])

        for _, r in df_p.iterrows():
            data.append([
                r["Estructura"],
                int(r["Cantidad"]),
                f"{r['Precio']:,.2f}",
                f"{r['Subtotal']:,.2f}",
            ])

        data.append([f"SUBTOTAL PUNTO {punto}", "", "", f"L {total:,.2f}"])

        tabla = Table(data, colWidths=[200, 60, 80, 100])
        tabla.setStyle(estilo_tabla())
        tabla.setStyle([
            ("SPAN", (0, -1), (2, -1)),
            ("ALIGN", (0, -1), (-1, -1), "RIGHT"),
        ])

        elementos.append(tabla)
        elementos.append(Spacer(1, 14))


# ======================================================
# 🚀 GENERADOR PDF
# ======================================================
def generar_pdf_contratista(entrada):

    if isinstance(entrada, pd.DataFrame):
        df_estructuras = entrada
        df_cables = None
    else:
        df_estructuras = getattr(entrada, "df_estructuras", None)
        df_cables = getattr(entrada, "df_cables", None)

    if df_estructuras is None:
        raise ValueError("No hay estructuras")

    df_puntos = calcular_estructuras_por_punto(df_estructuras)

    resultado = calcular_mano_obra_proyecto(df_puntos, df_cables)

    df_detalle = resultado["df_detalle"]
    df_totales = resultado["df_totales"]

    buffer = BytesIO()
    styles = getSampleStyleSheet()

    doc = SimpleDocTemplate(buffer, topMargin=120, leftMargin=40, rightMargin=40)

    elementos = []

    elementos.append(Paragraph("PRESUPUESTO DE INSTALACIÓN", styles["Title"]))
    elementos.append(Spacer(1, 16))
    elementos.append(tabla_presupuesto(df_detalle))
    elementos.append(PageBreak())

    pagina_resumen(elementos, styles, df_totales)
    pagina_resumen_global(elementos, styles, df_detalle)
    pagina_cotizacion(elementos, styles, doc, df_detalle)
    pagina_detalle(elementos, styles, df_detalle, df_totales)

    doc.build(elementos, onFirstPage=fondo_pagina, onLaterPages=fondo_pagina)

    pdf = buffer.getvalue()
    buffer.close()
    return pdf
