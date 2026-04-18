# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle


# =========================================================
# TABLA PRECIOS DE ESTRUCTURA (FORMATO OFERTA FINAL)
# =========================================================
def generar_tabla_precios_estructura(
    df_precios: pd.DataFrame,
    df_estructuras: pd.DataFrame | None = None,
):

    # =====================================================
    # VALIDACIONES
    # =====================================================
    if df_precios is None or not isinstance(df_precios, pd.DataFrame):
        raise ValueError("df_precios inválido")

    if df_precios.empty:
        raise ValueError("df_precios vacío")

    required_cols = ["Estructura", "Precio Unitario"]
    faltantes = [c for c in required_cols if c not in df_precios.columns]
    if faltantes:
        raise ValueError(f"df_precios no cumple contrato: {faltantes}")

    # =====================================================
    # AGRUPAR CANTIDADES (SOLO ESTRUCTURAS)
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
    # ESTILO TEXTO (CLAVE)
    # =====================================================
    style_small = ParagraphStyle(
        name="Small",
        fontName="Helvetica",
        fontSize=8,
        leading=9
    )

    # =====================================================
    # CABECERA
    # =====================================================
    data = [[
        "DESCRIPCIÓN",
        "P.U.",
        "CANT",
        "TOTAL"
    ]]

    total_general = 0.0

    # =====================================================
    # FILAS
    # =====================================================
    for _, r in df_precios.iterrows():

        estructura = str(r["Estructura"]).strip()
        pu = float(r["Precio Unitario"])

        cantidad = cantidades.get(estructura, None)

        # si no es estructura → usar su propia cantidad (cable)
        if cantidad is None or cantidad == 0:
            cantidad = float(r.get("Cantidad", 0))

        if cantidad <= 0:
            continue

        total = pu * cantidad

        # 🔥 TEXTO EN UNA SOLA LÍNEA
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
    # TABLA (AJUSTE FINAL)
    # =====================================================
    tabla = Table(
        data,
        colWidths=[320, 80, 60, 90]  # 🔥 ancho optimizado
    )

    tabla.setStyle(TableStyle([

        # HEADER
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

        # ALIGN
        ("ALIGN", (1, 1), (-1, -2), "RIGHT"),
        ("ALIGN", (2, 1), (2, -2), "CENTER"),

        # TOTAL
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EFEFEF")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),

        # GRID
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),

        # PADDING
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),

    ]))

    return [tabla]
