# -*- coding: utf-8 -*-
from __future__ import annotations
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from io import BytesIO
import pandas as pd
import streamlit as st

from materiales.calculos.calculo_estructuras import calcular_estructuras_por_punto
from costos_precios.mano_obra_por_punto import calcular_mano_obra_proyecto
from exportadores.pdf_base import fondo_pagina


# ======================================================
# 🎨 ESTILO TABLA
# ======================================================
def estilo_tabla():
    return [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3A5F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]


# ======================================================
# 🔴 TABLA GENERAL C1 (CON LOGÍSTICA)
# ======================================================
def tabla_presupuesto_general(df_detalle):

    df = df_detalle.groupby("Estructura", as_index=False).agg({
        "Cantidad": "sum",
        "Precio": "first",
        "Subtotal": "sum"
    })

    data = [["DESCRIPCIÓN", "P.U.", "CANT", "TOTAL"]]

    total_general = df_detalle["Subtotal"].sum()

    # 🔹 estructuras
    for _, r in df.iterrows():
        data.append([
            f"Instalación de {r['Estructura']}",
            f"L {r['Precio']:,.2f}",
            int(r["Cantidad"]),
            f"L {r['Subtotal']:,.2f}",
        ])

    # =====================================================
    # 🔥 LOGÍSTICA MANUAL
    # =====================================================
    if st.session_state.get("incluir_logistica", True):

        horas = st.session_state.get("horas_grua", 12)
        precio = st.session_state.get("precio_hora_grua", 1700)
        flete = st.session_state.get("costo_flete", 25000)
        viajes = st.session_state.get("viajes_flete", 1)
        ingenieria = st.session_state.get("ingenieria", 25000)

        total_grua = horas * precio
        total_flete = flete * viajes

        data.append(["Equipo Grúa", f"L {precio:,.2f}", horas, f"L {total_grua:,.2f}"])
        data.append(["Flete", f"L {flete:,.2f}", viajes, f"L {total_flete:,.2f}"])
        data.append(["Ingeniería", "", 1, f"L {ingenieria:,.2f}"])

        total_general += total_grua + total_flete + ingenieria

    data.append(["", "", "TOTAL GENERAL", f"L {total_general:,.2f}"])

    tabla = Table(data, colWidths=[320, 80, 60, 90])
    tabla.setStyle(estilo_tabla())

    return tabla


# ======================================================
# 🔵 TABLA BASE C2
# ======================================================
def tabla_presupuesto(df_detalle):

    df = df_detalle.groupby("Estructura", as_index=False).agg({
        "Cantidad": "sum",
        "Precio": "first",
        "Subtotal": "sum"
    })

    data = [["DESCRIPCIÓN", "P.U.", "CANT", "TOTAL"]]
    total = 0

    for _, r in df.iterrows():
        data.append([
            f"Instalación de {r['Estructura']}",
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
# 🔵 TABLA LOGÍSTICA (C2)
# ======================================================
def tabla_logistica():

    if not st.session_state.get("incluir_logistica", True):
        return None

    horas = st.session_state.get("horas_grua", 12)
    precio = st.session_state.get("precio_hora_grua", 1700)
    flete = st.session_state.get("costo_flete", 25000)
    viajes = st.session_state.get("viajes_flete", 1)
    ingenieria = st.session_state.get("ingenieria", 25000)

    total_grua = horas * precio
    total_flete = flete * viajes

    data = [
        ["DESCRIPCIÓN", "P.U.", "CANT", "TOTAL"],
        ["Equipo Grúa", f"L {precio:,.2f}", horas, f"L {total_grua:,.2f}"],
        ["Flete", f"L {flete:,.2f}", viajes, f"L {total_flete:,.2f}"],
        ["Ingeniería", "", 1, f"L {ingenieria:,.2f}"],
    ]

    tabla = Table(data, colWidths=[320, 80, 60, 90])
    tabla.setStyle(estilo_tabla())

    return tabla


# ======================================================
# 📄 GENERADOR PDF
# ======================================================
def generar_pdf_contratista(entrada):

    contratista = st.session_state.get("contratista", "C1")

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
    doc = SimpleDocTemplate(
        buffer,
        topMargin=160,   # 🔥 espacio para el membrete
        bottomMargin=40,
        leftMargin=40,
        rightMargin=40
    )

    elementos = []

    # ======================================================
    # 🔴 C1
    # ======================================================
    if contratista == "C1":

        elementos.append(Paragraph("CUADRO GENERAL DE PRECIOS", styles["Title"]))
        elementos.append(Spacer(1, 12))
        elementos.append(tabla_presupuesto_general(df_detalle))
        elementos.append(PageBreak())

    # ======================================================
    # 🔵 C2
    # ======================================================
    else:

        elementos.append(Paragraph("ESTRUCTURAS Y CONDUCTORES", styles["Title"]))
        elementos.append(tabla_presupuesto(df_detalle))
        elementos.append(PageBreak())

        elementos.append(Paragraph("MANO DE OBRA", styles["Title"]))
        elementos.append(tabla_presupuesto(df_detalle))
        elementos.append(PageBreak())

        tabla_log = tabla_logistica()
        if tabla_log:
            elementos.append(Paragraph("LOGÍSTICA", styles["Title"]))
            elementos.append(Spacer(1, 12))
            elementos.append(tabla_log)
            elementos.append(PageBreak())

    # ======================================================
    # RESUMEN
    # ======================================================
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

    doc.build(elementos, onFirstPage=fondo_pagina)

    pdf = buffer.getvalue()
    buffer.close()

    return pdf
