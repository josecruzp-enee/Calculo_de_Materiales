# -*- coding: utf-8 -*-
from __future__ import annotations

from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors


# =========================================================
# HELPERS
# =========================================================
def _fmt(valor: float) -> str:
    return f"L {valor:,.2f}"


# =========================================================
# COTIZACIÓN FINAL (FORMATO COMERCIAL)
# =========================================================
def generar_seccion_cotizacion_final(
    doc,
    styles,
    df_precios,
    df_estructuras,
    porcentaje_gestion: float = 0.02,
    porcentaje_imprevistos: float = 0.01,
    porcentaje_isv: float = 0.15,
):

    elems = []  # 🔥 FIX

    if df_precios is None or df_precios.empty:
        raise ValueError("df_precios vacío")

    if df_estructuras is None or df_estructuras.empty:
        raise ValueError("df_estructuras vacío")

    df_estructuras = df_estructuras.copy()
    df_estructuras["Estructura"] = df_estructuras["Estructura"].astype(str).str.strip()

    cantidades = (
        df_estructuras.groupby("Estructura")["Cantidad"]
        .sum()
        .to_dict()
    )

    total_base = 0.0

    for _, r in df_precios.iterrows():
        estructura = str(r["Estructura"]).strip()
        pu = float(r["Precio Unitario"])
        cant = float(cantidades.get(estructura, 1))

        total_base += pu * cant

    gestion = total_base * porcentaje_gestion
    imprevistos = total_base * porcentaje_imprevistos

    subtotal = total_base + gestion + imprevistos
    isv = subtotal * porcentaje_isv
    total_final = subtotal + isv

    elems.append(Paragraph("<b>COTIZACIÓN DEL PROYECTO</b>", styles["Heading1"]))
    elems.append(Spacer(1, 12))

    data = [
        ["Concepto", "Monto (L)"],
        ["Suministro e instalación del proyecto eléctrico", _fmt(total_base)],
        ["Gestión y aprobación ENEE (2%)", _fmt(gestion)],
        ["Imprevistos (1%)", _fmt(imprevistos)],
        ["SUBTOTAL", _fmt(subtotal)],
        ["ISV (15%)", _fmt(isv)],
        ["TOTAL OFERTA", _fmt(total_final)],
    ]

    tabla = Table(
        data,
        colWidths=[doc.width * 0.7, doc.width * 0.3]
    )

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),

        ("BACKGROUND", (0, -1), (-1, -1), colors.darkblue),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),

        ("BACKGROUND", (0, -3), (-1, -3), colors.HexColor("#EFEFEF")),
        ("FONTNAME", (0, -3), (-1, -3), "Helvetica-Bold"),

        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elems.append(tabla)
    elems.append(Spacer(1, 12))

    elems.append(
        Paragraph(
            "<font size=8><i>"
            "Esta oferta incluye suministro de materiales, instalación, gestión ante ENEE "
            "y costos asociados para la ejecución del proyecto."
            "</i></font>",
            styles["Normal"]
        )
    )

    return elems
