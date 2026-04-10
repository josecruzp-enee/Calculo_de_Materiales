# -*- coding: utf-8 -*-
"""
exportadores/pdf_anexos_costos.py

Anexos de costos:
A - Materiales
B - Costos por estructura (desglosado)
C - Costos por punto
"""

import re
import pandas as pd
from xml.sax.saxutils import escape
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.units import inch

from exportadores.pdf_base import styles, styleN, formatear_material


# ==========================================================
# UTIL
# ==========================================================
def _money(v):
    if v is None or pd.isna(v):
        return ""
    return f"L {float(v):,.2f}"


# ==========================================================
# ANEXO A: COSTOS DE MATERIALES
# ==========================================================
def tabla_costos_materiales_pdf(df_costos: pd.DataFrame):

    titulo = Paragraph("ANEXO A – Costos de Materiales", styles["Heading2"])
import pandas as pd

    if df_costos is None or df_costos.empty:
        return [titulo, Paragraph("No hay datos disponibles.", styles["Normal"])]

    df = df_costos.copy()
    df.columns = [str(c).strip() for c in df.columns]
# =========================================================
# HELPERS
# =========================================================
def _validar_df(df: pd.DataFrame, nombre: str):
    if df is None or not isinstance(df, pd.DataFrame):
        raise ValueError(f"{nombre} inválido")

    df["Cantidad"] = pd.to_numeric(df.get("Cantidad", 0), errors="coerce").fillna(0)
    df["Precio Unitario"] = pd.to_numeric(df.get("Precio Unitario", 0), errors="coerce")
    df["Costo"] = pd.to_numeric(df.get("Costo", 0), errors="coerce")
    if df.empty:
        raise ValueError(f"{nombre} vacío")

    subtotal = df["Costo"].sum()
    iva = subtotal * 0.15
    total = subtotal + iva

    data = [["Material", "Unidad", "Cantidad", "P.U.", "Costo"]]
def _fmt_moneda(valor: float) -> str:
    return f"L {valor:,.0f}" if valor % 1 == 0 else f"L {valor:,.2f}"

    for _, r in df.iterrows():
        data.append([
            Paragraph(formatear_material(str(r.get("Materiales", ""))), styleN),
            escape(str(r.get("Unidad", ""))),
            f"{r['Cantidad']:,.2f}",
            _money(r["Precio Unitario"]),
            _money(r["Costo"]),
        ])

    data.append(["", "", "", "SUBTOTAL", _money(subtotal)])
    data.append(["", "", "", "ISV 15%", _money(iva)])
    data.append(["", "", "", "TOTAL", _money(total)])

    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
    ]))
# =========================================================
# REPORTE COSTOS DE ESTRUCTURAS (PRESUPUESTO)
# =========================================================
def generar_tabla_costos_estructura(
    doc,
    styles,
    df_costos_estructura: pd.DataFrame,
):

    return [titulo, Spacer(1, 8), t]
    # =====================================================
    # VALIDACIÓN
    # =====================================================
    _validar_df(df_costos_estructura, "df_costos_estructura")

    df = df_costos_estructura.copy()

# ==========================================================
# ANEXO B: COSTOS POR ESTRUCTURA (NUEVO MODELO)
# ==========================================================
def tabla_costos_estructuras_pdf(df_costos_estructuras: pd.DataFrame):
    # =====================================================
    # NORMALIZAR NOMBRE
    # =====================================================
    if "Estructura" not in df.columns:
        if "codigodeestructura" in df.columns:
            df["Estructura"] = df["codigodeestructura"]
        else:
            raise ValueError("No existe columna 'Estructura'")

    titulo = Paragraph("ANEXO B – Costos por Estructura", styles["Heading2"])
    required = ["Estructura", "Cantidad", "Costo Unitario", "Costo Total"]
    faltantes = [c for c in required if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas: {faltantes}")

    if df_costos_estructuras is None or df_costos_estructuras.empty:
        return [titulo, Paragraph("No hay datos disponibles.", styles["Normal"])]

    df = df_costos_estructuras.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # -----------------------------------------------------
    # =====================================================
    # NORMALIZACIÓN
    # -----------------------------------------------------
    if "codigodeestructura" not in df.columns:
        raise ValueError("Falta codigodeestructura")

    df["Cantidad"] = pd.to_numeric(df.get("Cantidad", 0), errors="coerce").fillna(0)

    # 🔥 NUEVAS COLUMNAS ESPERADAS
    for col in [
        "Costo Material",
        "Costo Operativo",
        "Costo Unitario",
        "Precio Unitario"
    ]:
        if col not in df.columns:
            df[col] = 0.0

    # -----------------------------------------------------
    # TABLA
    # -----------------------------------------------------
    data = [[
        "Estructura",
        "Cant",
        "Material",
        "Operativo",
        "Costo",
        "Precio"
    ]]

    total_costo = 0
    total_precio = 0
    # =====================================================
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)
    df["Costo Unitario"] = pd.to_numeric(df["Costo Unitario"], errors="coerce").fillna(0)
    df["Costo Total"] = pd.to_numeric(df["Costo Total"], errors="coerce").fillna(0)

    for _, r in df.iterrows():
    df = df.sort_values("Estructura").reset_index(drop=True)

        cod = str(r["codigodeestructura"])
        cant = int(r["Cantidad"])
    # =====================================================
    # TABLA
    # =====================================================
    data = [["ITEM", "ESTRUCTURA", "CANT", "P.U.", "TOTAL"]]

        mat = float(r["Costo Material"])
        op = float(r["Costo Operativo"])
        costo = float(r["Costo Unitario"])
        precio = float(r["Precio Unitario"])
    total_general = float(df["Costo Total"].sum())

        total_costo += costo * cant
        total_precio += precio * cant
    for i, (_, row) in enumerate(df.iterrows(), start=1):

        data.append([
            Paragraph(escape(cod), styleN),
            f"{cant}",
            _money(mat),
            _money(op),
            _money(costo),
            _money(precio),
            f"{i:02d}",
            str(row["Estructura"]),
            f"{int(row['Cantidad'])}",
            _fmt_moneda(row["Costo Unitario"]),
            _fmt_moneda(row["Costo Total"]),
        ])

    # Totales
    data.append(["", "", "", "TOTAL COSTO", _money(total_costo), ""])
    data.append(["", "", "", "TOTAL PRECIO", "", _money(total_precio)])

    t = Table(
    # TOTAL GENERAL
    data.append([
        "",
        "TOTAL GENERAL",
        "",
        "",
        _fmt_moneda(total_general)
    ])

    # =====================================================
    # FORMATO
    # =====================================================
    tabla = Table(
        data,
        repeatRows=1,
        colWidths=[1.2*inch, 0.7*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch]
        colWidths=[
            doc.width * 0.08,
            doc.width * 0.32,
            doc.width * 0.12,
            doc.width * 0.20,
            doc.width * 0.28,
        ]
    )

    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("ALIGN", (1, 1), (1, -1), "CENTER"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))

    return [titulo, Spacer(1, 8), t]


# ==========================================================
# ANEXO C: COSTOS POR PUNTO
# ==========================================================
def tabla_costos_por_punto_pdf(df_detalle: pd.DataFrame):

    titulo = Paragraph("ANEXO C – Costos por Punto", styles["Heading2"])

    if df_detalle is None or df_detalle.empty:
        return [titulo, Paragraph("No hay datos disponibles.", styles["Normal"])]
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.darkblue),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),

    elems = [titulo, Spacer(1, 8)]
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),

    df = df_detalle.copy()
    df.columns = [str(c).strip() for c in df.columns]
        ("ALIGN", (2,1), (2,-2), "CENTER"),
        ("ALIGN", (3,1), (4,-2), "RIGHT"),

    puntos = sorted(df["Punto"].unique())

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

        t = Table(data, colWidths=[3*inch, 2*inch])
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ]))
        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#EFEFEF")),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
    ]))

        elems.append(t)
        elems.append(Spacer(1, 8))
    elems = []
    elems.append(Paragraph("<b>2. PRESUPUESTO DE ESTRUCTURAS</b>", styles["Heading2"]))
    elems.append(Spacer(1, 8))
    elems.append(tabla)

    return elems
