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
import streamlit as st

from materiales.calculos.calculo_estructuras import calcular_estructuras_por_punto
from costos_precios.mano_obra_por_punto import calcular_mano_obra_proyecto
from exportadores.pdf_base import fondo_pagina


# ======================================================
# ⚙️ CONFIG LOGÍSTICA DINÁMICA
# ======================================================
def cfg_logistica():
    return {
        "horas_poste": st.session_state.get("horas_grua_poste", 3),
        "precio_hora": st.session_state.get("precio_hora_grua", 1700),
        "flete": st.session_state.get("costo_flete", 25000),
        "viajes": st.session_state.get("viajes_flete", 2),
        "ingenieria": st.session_state.get("ingenieria", 25000),
    }


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
# 🔥 TABLA GENERAL (C1 CON LOGÍSTICA)
# ======================================================
def tabla_presupuesto_general(df_detalle):

    cfg = cfg_logistica()

    df = df_detalle.groupby("Estructura", as_index=False).agg({
        "Cantidad": "sum",
        "Precio": "first",
        "Subtotal": "sum"
    })

    data = [["DESCRIPCIÓN", "P.U.", "CANT", "TOTAL"]]

    total = df_detalle["Subtotal"].sum()

    for _, r in df.iterrows():
        data.append([
            f"Instalación de {r['Estructura']}",
            f"L {r['Precio']:,.2f}",
            int(r["Cantidad"]),
            f"L {r['Subtotal']:,.2f}",
        ])

    # 🔥 LOGÍSTICA DINÁMICA
    postes = df[df["Estructura"].str.contains("PC-")]["Cantidad"].sum()

    horas = postes * cfg["horas_poste"]
    total_grua = horas * cfg["precio_hora"]
    total_flete = cfg["flete"] * cfg["viajes"]

    data.append(["Equipo Grúa", f"L {cfg['precio_hora']:,.2f}", horas, f"L {total_grua:,.2f}"])
    data.append(["Flete", f"L {cfg['flete']:,.2f}", cfg["viajes"], f"L {total_flete:,.2f}"])
    data.append(["Ingeniería", "", 1, f"L {cfg['ingenieria']:,.2f}"])

    total_general = total + total_grua + total_flete + cfg["ingenieria"]

    data.append(["", "", "TOTAL GENERAL", f"L {total_general:,.2f}"])

    tabla = Table(data, colWidths=[320, 80, 60, 90])
    tabla.setStyle(estilo_tabla())

    return tabla


# ======================================================
# 🔹 TABLA BASE (C2)
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
# 📄 GENERADOR PDF
# ======================================================
def generar_pdf_contratista(entrada):

    contratista = st.session_state.get("contratista", "C1")

    # =============================
    # ENTRADAS
    # =============================
    if isinstance(entrada, pd.DataFrame):
        df_estructuras = entrada
        df_cables = None
    else:
        df_estructuras = getattr(entrada, "df_estructuras", None)
        df_cables = getattr(entrada, "df_cables", None)

    if df_estructuras is None:
        raise ValueError("No hay estructuras")

    # =============================
    # CÁLCULO
    # =============================
    df_puntos = calcular_estructuras_por_punto(df_estructuras)

    resultado = calcular_mano_obra_proyecto(df_puntos, df_cables)

    df_detalle = resultado["df_detalle"]
    df_totales = resultado["df_totales"]

    # =============================
    # PDF
    # =============================
    buffer = BytesIO()
    styles = getSampleStyleSheet()

    doc = SimpleDocTemplate(buffer)

    elementos = []

    # ======================================================
    # 🔴 C1 → TODO INCLUIDO
    # ======================================================
    if contratista == "C1":

        elementos.append(Paragraph("CUADRO GENERAL DE PRECIOS", styles["Title"]))
        elementos.append(Spacer(1, 12))
        elementos.append(tabla_presupuesto_general(df_detalle))
        elementos.append(PageBreak())

    # ======================================================
    # 🔵 C2 → SEPARADO
    # ======================================================
    else:

        elementos.append(Paragraph("ESTRUCTURAS Y CONDUCTORES", styles["Title"]))
        elementos.append(tabla_presupuesto(df_detalle))
        elementos.append(PageBreak())

        elementos.append(Paragraph("MANO DE OBRA", styles["Title"]))
        elementos.append(tabla_presupuesto(df_detalle))
        elementos.append(PageBreak())

    # ======================================================
    # COMUNES
    # ======================================================
    from reportlab.platypus import Spacer

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
