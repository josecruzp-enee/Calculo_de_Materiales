# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from exportadores.pdf_base import estilo_tabla

# =========================================================
# TABLA PRECIOS DE ESTRUCTURA (FORMATO OFERTA FINAL)
# =========================================================
def generar_tabla_precios_estructura(
    df_precios: pd.DataFrame,
    df_estructuras: pd.DataFrame | None = None,
):

    from reportlab.platypus import Table, TableStyle, Paragraph
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle

    # =====================================================
    # VALIDACIONES
    # =====================================================
    if df_precios is None or not isinstance(df_precios, pd.DataFrame):
        raise ValueError("df_precios inválido")

    if df_precios.empty:
        raise ValueError("df_precios vacío")

    # =====================================================
    # ESTILO TEXTO (CLAVE)
    # =====================================================
    style_small = ParagraphStyle(
        name="Small",
        fontName="Helvetica",
        fontSize=8,
        leading=9
    )

    # =====================================================
    # AGRUPAR CANTIDADES
    # =====================================================
    cantidades = {}

    if df_estructuras is not None and not df_estructuras.empty:

        df_tmp = df_estructuras.copy()
        df_tmp["Estructura"] = df_tmp["Estructura"].astype(str).str.strip()
        df_tmp["Cantidad"] = pd.to_numeric(df_tmp["Cantidad"], errors="coerce").fillna(0)

        cantidades = (
            df_tmp.groupby("Estructura")["Cantidad"]
            .sum()
            .to_dict()
        )

    # =====================================================
    # CABECERA
    # =====================================================
    data = [["DESCRIPCIÓN", "P.U.", "CANT", "TOTAL"]]

    total_general = 0.0

    # =====================================================
    # FILAS
    # =====================================================
    for _, r in df_precios.iterrows():

        estructura = str(r["Estructura"]).strip()
        pu = float(r["Precio Unitario"])

        cantidad = cantidades.get(estructura, None)

        if cantidad is None or cantidad == 0:
            cantidad = float(r.get("Cantidad", 0))

        if cantidad <= 0:
            continue

        total = pu * cantidad

        # 🔥 TEXTO LIMPIO EN UNA SOLA LÍNEA
        texto = f"Suministro e instalación de estructura tipo {estructura}"
        descripcion = Paragraph(texto, style_small)

        total_general += total

        data.append([
            descripcion,
            f"L {pu:,.2f}",
            f"{int(cantidad)}",
            f"L {total:,.2f}",
        ])

    # =====================================================
    # CONTROL VACÍO
    # =====================================================
    if len(data) == 1:
        data.append(["SIN DATOS", "-", "-", "-"])

    # =====================================================
    # TOTAL
    # =====================================================
    data.append([
        "",
        "",
        "TOTAL",
        f"L {total_general:,.2f}"
    ])

    # =====================================================
    # TABLA
    # =====================================================
    tabla = Table(
        data,
        colWidths=[320, 80, 60, 90]  # 🔥 ancho corregido
    )

    tabla.setStyle(TableStyle([

        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

        ("ALIGN", (1, 1), (-1, -2), "RIGHT"),
        ("ALIGN", (2, 1), (2, -2), "CENTER"),

        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EFEFEF")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),

        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),

        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))

    return [tabla]

# =========================================================
# COTIZACIÓN SIMPLE (RESTAURADA)
# =========================================================
def generar_cotizacion_desde_estructuras(doc, styles, df_precios):

    from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors

    elems = []

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    if df_precios is None or df_precios.empty:
        elems.append(Paragraph("SIN DATOS PARA COTIZACIÓN", styles["Normal"]))
        return elems

    # =====================================================
    # TOTAL BASE
    # =====================================================
    if "Subtotal" in df_precios.columns:
        total_base = float(df_precios["Subtotal"].sum())
    else:
        total_base = float(df_precios["Precio Total"].sum())

    # =====================================================
    # GASTOS DE INGENIERÍA
    # =====================================================
    ingenieria = total_base * 0.15

    subtotal = total_base + ingenieria
    isv = subtotal * 0.15
    total_final = subtotal + isv

    # =====================================================
    # TÍTULO
    # =====================================================
    elems.append(Paragraph("<b>COTIZACIÓN DEL PROYECTO</b>", styles["Heading1"]))
    elems.append(Spacer(1, 12))

    # =====================================================
    # TABLA
    # =====================================================
    data = [
        ["Concepto", "Monto (L)"],
        ["Suministro e instalación", f"L {total_base:,.2f}"],
        ["Gastos de Ingeniería (15%)", f"L {ingenieria:,.2f}"],
        ["SUBTOTAL", f"L {subtotal:,.2f}"],
        ["ISV (15%)", f"L {isv:,.2f}"],
        ["TOTAL PROYECTO", f"L {total_final:,.2f}"],
    ]

    tabla = Table(data, colWidths=[doc.width * 0.7, doc.width * 0.3])

    tabla.setStyle(TableStyle([

        # HEADER
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

        # ALIGN
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),

        # TOTAL FINAL
        ("BACKGROUND", (0, -1), (-1, -1), colors.darkblue),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),

        # GRID
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),

    ]))

    elems.append(tabla)

    return elems
