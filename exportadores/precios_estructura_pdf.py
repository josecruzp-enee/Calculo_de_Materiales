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

    ✔ Soporta estructuras (desde df_estructuras)
    ✔ Soporta cable (usa Cantidad del df_precios)
    """

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

        if "Estructura" not in df_estructuras.columns or "Cantidad" not in df_estructuras.columns:
            raise ValueError("df_estructuras debe tener 'Estructura' y 'Cantidad'")

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

        # 🔥 INTENTA SACAR CANTIDAD DESDE ESTRUCTURAS
        cantidad = cantidades.get(estructura, None)

        # 🔥 SI NO EXISTE → ES CABLE → USA SU PROPIA CANTIDAD
        if cantidad is None or cantidad == 0:
            cantidad = float(r.get("Cantidad", 0))

        # si sigue sin valor → no mostrar
        if cantidad <= 0:
            continue

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
    # CONTROL SI NO HAY FILAS
    # =====================================================
    if len(data) == 1:
        data.append(["SIN DATOS", "-", "-", "-"])

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
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

        ("ALIGN", (1, 1), (-1, -2), "RIGHT"),
        ("ALIGN", (2, 1), (2, -2), "CENTER"),

        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EFEFEF")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),

        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),

        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))

    return [tabla]

# =========================================================
# COTIZACIÓN SIMPLE (DESDE PRECIOS DE ESTRUCTURA)
# =========================================================
def generar_cotizacion_desde_estructuras(doc, styles, df_precios):

    from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors

    elems = []

    if df_precios is None or df_precios.empty:
        elems.append(Paragraph("SIN DATOS PARA COTIZACIÓN", styles["Normal"]))
        return elems

    # 🔥 TOTAL REAL DEL PRESUPUESTO
    total_base = float(df_precios["Subtotal"].sum())

    # =====================================================
    # GASTOS
    # =====================================================
    enee = total_base * 0.02
    imprevistos = total_base * 0.01

    subtotal = total_base + enee + imprevistos
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
        ["Gestión ENEE (2%)", f"L {enee:,.2f}"],
        ["Imprevistos (1%)", f"L {imprevistos:,.2f}"],
        ["SUBTOTAL", f"L {subtotal:,.2f}"],
        ["ISV (15%)", f"L {isv:,.2f}"],
        ["TOTAL PROYECTO", f"L {total_final:,.2f}"],
    ]

    tabla = Table(data, colWidths=[doc.width * 0.7, doc.width * 0.3])

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),

        ("BACKGROUND", (0, -1), (-1, -1), colors.darkblue),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),

        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elems.append(tabla)

    return elems
