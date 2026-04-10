# -*- coding: utf-8 -*-

import pandas as pd
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

from exportadores.pdf_base import styles, styleN, formatear_material


# =========================================================
# HELPERS
# =========================================================
def _money(v):
    if v is None or pd.isna(v):
        return ""
    return f"L {float(v):,.2f}"


# =========================================================
# ANEXO A — COSTOS DE MATERIALES
# =========================================================
def tabla_costos_materiales_pdf(df_costos: pd.DataFrame):

    titulo = Paragraph("ANEXO A – Costos de Materiales", styles["Heading2"])

    if df_costos is None or df_costos.empty:
        return [titulo, Paragraph("No hay datos disponibles.", styles["Normal"])]

    df = df_costos.copy()
    df["Cantidad"] = pd.to_numeric(df.get("Cantidad", 0), errors="coerce").fillna(0)
    df["Costo Unitario"] = pd.to_numeric(df.get("Costo Unitario", 0), errors="coerce")
    df["Costo Total"] = pd.to_numeric(df.get("Costo Total", 0), errors="coerce")

    data = [["Material", "Unidad", "Cantidad", "P.U.", "Costo"]]

    for _, r in df.iterrows():
        data.append([
            Paragraph(formatear_material(str(r.get("Materiales", ""))), styleN),
            str(r.get("Unidad", "")),
            f"{r['Cantidad']:,.2f}",
            _money(r["Costo Unitario"]),
            _money(r["Costo Total"]),
        ])

    tabla = Table(data, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
    ]))

    return [titulo, Spacer(1, 8), tabla]


# =========================================================
# ANEXO B — COSTOS POR ESTRUCTURA (RESUMEN)
# =========================================================
def tabla_costos_estructuras_pdf(df_costos_estructuras: pd.DataFrame):

    titulo = Paragraph("ANEXO B – Costos por Estructura", styles["Heading2"])

    if df_costos_estructuras is None or df_costos_estructuras.empty:
        return [titulo, Paragraph("No hay datos disponibles.", styles["Normal"])]

    df = df_costos_estructuras.copy()

    if "Estructura" not in df.columns:
        if "codigodeestructura" in df.columns:
            df["Estructura"] = df["codigodeestructura"]
        else:
            raise ValueError("No existe columna 'Estructura'")

    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)
    df["Costo Unitario"] = pd.to_numeric(df["Costo Unitario"], errors="coerce").fillna(0)
    df["Costo Total"] = pd.to_numeric(df["Costo Total"], errors="coerce").fillna(0)

    data = [["Estructura", "Cantidad", "Costo Unitario", "Total"]]

    for _, r in df.iterrows():
        data.append([
            str(r["Estructura"]),
            f"{int(r['Cantidad'])}",
            _money(r["Costo Unitario"]),
            _money(r["Costo Total"]),
        ])

    tabla = Table(data, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
    ]))

    return [titulo, Spacer(1, 8), tabla]


# =========================================================
# ANEXO C — COSTOS POR PUNTO
# =========================================================
def tabla_costos_por_punto_pdf(df_detalle: pd.DataFrame):

    titulo = Paragraph("ANEXO C – Costos por Punto", styles["Heading2"])

    if df_detalle is None or df_detalle.empty:
        return [titulo, Paragraph("No hay datos disponibles.", styles["Normal"])]

    df = df_detalle.copy()

    puntos = sorted(df["Punto"].unique())
    elems = [titulo, Spacer(1, 8)]

    for p in puntos:

        elems.append(Paragraph(f"<b>Punto {p}</b>", styles["Heading3"]))

        df_p = df[df["Punto"] == p]

        subtotal_costo = df_p["Subtotal Costo"].sum()
        subtotal_precio = df_p["Subtotal Precio"].sum()

        data = [
            ["Concepto", "Monto"],
            ["Costo", _money(subtotal_costo)],
            ["Precio", _money(subtotal_precio)],
        ]

        tabla = Table(data, colWidths=[3*inch, 2*inch])
        tabla.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ]))

        elems.append(tabla)
        elems.append(Spacer(1, 8))

    return elems
