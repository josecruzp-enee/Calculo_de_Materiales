# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors


# =========================================================
# TABLA PRECIOS DE ESTRUCTURA (FORMATO OFERTA)
# =========================================================
def generar_tabla_precios_estructura(
    df_precios: pd.DataFrame,
    df_estructuras: pd.DataFrame | None = None,
):
    """
    Renderiza precios en formato:

    Descripción | PU | Cantidad | Total
    """

    if df_precios is None or df_precios.empty:
        raise ValueError("df_precios vacío")

    # =====================================================
    # AGRUPAR CANTIDADES (SI SE PROPORCIONA)
    # =====================================================
    cantidades = {}

    if df_estructuras is not None and not df_estructuras.empty:
        df_tmp = df_estructuras.copy()
        df_tmp["Estructura"] = df_tmp["Estructura"].astype(str).str.strip()

        cantidades = (
            df_tmp.groupby("Estructura")["Cantidad"]
            .sum()
            .to_dict()
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

        cantidad = cantidades.get(estructura, 1)  # fallback
        total = pu * cantidad

        descripcion = f"Suministro e instalación de estructura tipo {estructura}"

        total_general += total

        data.append([
            descripcion,
            f"L {pu:,.2f}",
            f"{int(cantidad)}",
            f"L {total:,.2f}",
        ])

    # =====================================================
    # TOTAL GENERAL
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
        colWidths=[280, 90, 60, 100]
    )

    tabla.setStyle(TableStyle([
        # encabezado
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

        # alineación
        ("ALIGN", (1, 1), (-1, -2), "RIGHT"),
        ("ALIGN", (2, 1), (2, -2), "CENTER"),

        # total
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EFEFEF")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),

        # grid
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),

        # padding
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))

    return [tabla]
