# -*- coding: utf-8 -*-
"""
exportadores/pdf_anexos_costos.py
Anexos de costos (A/B/C).
Autor: José Nikol Cruz
"""

import re
import pandas as pd
from xml.sax.saxutils import escape
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

from exportadores.pdf_base import styles, styleN, formatear_material


# ==========================================================
# ANEXO: COSTOS DE MATERIALES (TABLA)
# ==========================================================
def tabla_costos_materiales_pdf(df_costos: pd.DataFrame):
    """
    Construye flowables ReportLab para el anexo de costos.
    Formato de moneda: "L 5.00"
    """
    titulo = Paragraph("ANEXO – Costos de Materiales", styles["Heading2"])

    if df_costos is None or df_costos.empty:
        return [titulo, Paragraph("No hay datos de costos disponibles.", styles["Normal"])]

    df = df_costos.copy()

    # Normalizar columnas
    df.columns = [str(c).replace("\u00A0", " ").strip() for c in df.columns]

    # Aliases
    ren = {}
    for c in df.columns:
        cc = c.lower().replace(" ", "_")
        if cc in {"material", "materiales", "descripcion", "descripción"}:
            ren[c] = "Materiales"
        elif cc in {"unidad", "unid"}:
            ren[c] = "Unidad"
        elif cc in {"cantidad", "qty"}:
            ren[c] = "Cantidad"
        elif cc in {"precio_unitario", "precio", "costo_unitario"}:
            ren[c] = "Precio Unitario"
        elif cc in {"costo", "costo_total", "costototal"}:
            ren[c] = "Costo Total"
    df = df.rename(columns=ren)

    # Columnas mínimas defensivas
    for c, default in [
        ("Materiales", ""),
        ("Unidad", ""),
        ("Cantidad", 0.0),
        ("Precio Unitario", pd.NA),
        ("Costo Total", pd.NA),
    ]:
        if c not in df.columns:
            df[c] = default

    # Numéricos
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0.0)
    df["Precio Unitario"] = pd.to_numeric(df["Precio Unitario"], errors="coerce")
    df["Costo Total"] = pd.to_numeric(df["Costo Total"], errors="coerce")

    df["Tiene_Precio"] = (df["Precio Unitario"].fillna(0.0) > 0)
    df = df.sort_values(["Tiene_Precio", "Materiales"], ascending=[False, True])

    subtotal = df.loc[df["Tiene_Precio"] == True, "Costo Total"].fillna(0.0).sum()
    iva = subtotal * 0.15
    total = subtotal + iva

    def _money(v):
        if v is None or pd.isna(v):
            return ""
        return f"L {float(v):,.2f}"

    data = [["Materiales", "Unidad", "Cantidad", "Precio Unitario", "Costo Total"]]

    for _, r in df.iterrows():
        mat = str(r.get("Materiales", "") or "")
        uni = str(r.get("Unidad", "") or "")
        cant = float(r.get("Cantidad", 0) or 0)

        pu = r.get("Precio Unitario", None)
        ct = r.get("Costo Total", None)

        data.append([
            Paragraph(formatear_material(mat), styleN),
            escape(uni),
            f"{cant:,.2f}",
            _money(pu),
            _money(ct),
        ])

    data.append(["", "", "", "SUBTOTAL", _money(subtotal)])
    data.append(["", "", "", "ISV 15%", _money(iva)])
    data.append(["", "", "", "TOTAL", _money(total)])

    t = Table(
        data,
        repeatRows=1,
        colWidths=[3.7 * inch, 0.8 * inch, 0.9 * inch, 1.2 * inch, 1.2 * inch],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (1, 1), (1, -2), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (3, -3), (4, -1), "Helvetica-Bold"),
    ]))

    faltan = int((df["Tiene_Precio"] == False).sum())
    nota = Paragraph(
        f"Nota: {faltan} material(es) no tienen precio cargado.",
        styles["Normal"]
    )

    return [Spacer(1, 8), titulo, Spacer(1, 8), t, Spacer(1, 8), nota]


# ==========================================================
# ANEXO B: COSTOS POR ESTRUCTURA (TABLA)
# ==========================================================
def tabla_costos_estructuras_pdf(df_costos_estructuras: pd.DataFrame):
    titulo = Paragraph("ANEXO B – Costos por Estructura", styles["Heading2"])

    if df_costos_estructuras is None or df_costos_estructuras.empty:
        return [titulo, Paragraph("No hay datos de costos por estructura disponibles.", styles["Normal"])]

    df = df_costos_estructuras.copy()
    df.columns = [str(c).replace("\u00A0", " ").strip() for c in df.columns]

    # Normalizar nombres flexibles
    if "codigodeestructura" not in df.columns:
        if "Estructura" in df.columns:
            df["codigodeestructura"] = df["Estructura"]
        else:
            df["codigodeestructura"] = ""

    if "Descripcion" not in df.columns:
        if "Descripción" in df.columns:
            df["Descripcion"] = df["Descripción"]
        else:
            df["Descripcion"] = ""

    for col, default in [("Cantidad", 0), ("Costo Unitario", 0.0), ("Costo Total", 0.0)]:
        if col not in df.columns:
            df[col] = default

    # Tipos
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0).astype(int)
    df["Costo Unitario"] = pd.to_numeric(df["Costo Unitario"], errors="coerce").fillna(0.0)
    df["Costo Total"] = pd.to_numeric(df["Costo Total"], errors="coerce").fillna(0.0)

    df = df.sort_values(["codigodeestructura"], ascending=[True])

    def _money(v):
        if v is None or pd.isna(v):
            return ""
        return f"L {float(v):,.2f}"

    data = [["Estructura", "Descripción", "Cantidad", "Costo Unitario", "Costo Total"]]

    for _, r in df.iterrows():
        cod = str(r.get("codigodeestructura", "") or "").strip()
        desc = str(r.get("Descripcion", "") or "").strip()
        cant = int(r.get("Cantidad", 0) or 0)

        data.append([
            Paragraph(escape(cod), styleN),
            Paragraph(escape(desc), styleN),
            f"{cant:d}",
            _money(r.get("Costo Unitario", 0.0)),
            _money(r.get("Costo Total", 0.0)),
        ])

    total_general = float(df["Costo Total"].sum())
    data.append(["", "", "", "TOTAL", _money(total_general)])

    t = Table(
        data,
        repeatRows=1,
        colWidths=[1.1 * inch, 3.1 * inch, 0.8 * inch, 1.2 * inch, 1.2 * inch],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 1), (2, -2), "CENTER"),
        ("ALIGN", (3, 1), (4, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (3, -1), (4, -1), "Helvetica-Bold"),
    ]))

    nota = Paragraph(
        "Nota: El costo por estructura se calcula como la suma de (cantidad_material × precio_unitario) "
        "para una (1) estructura, multiplicado por la cantidad total de esa estructura en el proyecto.",
        styles["Normal"]
    )

    return [Spacer(1, 8), titulo, Spacer(1, 8), t, Spacer(1, 8), nota]


# ==========================================================
# ANEXO C: COSTOS POR PUNTO
# ==========================================================
def tabla_costos_por_punto_pdf(df_mat_por_punto: pd.DataFrame):
    titulo = Paragraph("ANEXO C – Costos por Punto", styles["Heading2"])

    if df_mat_por_punto is None or df_mat_por_punto.empty:
        return [titulo, Paragraph("No hay costos por punto disponibles.", styles["Normal"])]

    elems = [titulo, Spacer(1, 8)]

    df = df_mat_por_punto.copy()
    df.columns = [str(c).strip() for c in df.columns]

    puntos = sorted(
        df["Punto"].unique(),
        key=lambda x: int(re.sub(r"\D", "", str(x)) or 0)
    )

    for p in puntos:
        elems.append(Spacer(1, 6))
        elems.append(Paragraph(f"<b>Punto {escape(str(p))}</b>", styles["Heading3"]))

        df_p = df[df["Punto"] == p]

        df_mt = df_p[df_p["Materiales"].str.contains("MT|PRIMARIA", case=False, na=False)]
        df_bt = df_p[~df_p.index.isin(df_mt.index)]

        def _subtotal(df_x):
            return df_x["Costo Total"].fillna(0).sum()

        sub_mt = _subtotal(df_mt)
        sub_bt = _subtotal(df_bt)
        subtotal = sub_mt + sub_bt
        impuesto = subtotal * 0.15
        total = subtotal + impuesto

        data = [
            ["Concepto", "Monto (L)"],
            ["Materiales MT", f"L {sub_mt:,.2f}"],
            ["Materiales BT", f"L {sub_bt:,.2f}"],
            ["SUBTOTAL", f"L {subtotal:,.2f}"],
            ["Impuesto 15%", f"L {impuesto:,.2f}"],
            ["TOTAL", f"L {total:,.2f}"],
        ]

        t = Table(data, colWidths=[3 * inch, 2 * inch])
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTNAME", (0, 3), (-1, -1), "Helvetica-Bold"),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ]))

        elems.append(t)

    return elems
