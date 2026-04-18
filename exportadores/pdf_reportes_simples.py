# -*- coding: utf-8 -*-
"""
exportadores/pdf_reportes_simples.py
Reportes PDF unitarios: materiales/estructuras global y por punto.
Autor: José Nikol Cruz
"""

import re
import pandas as pd
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors

from exportadores.pdf_base import (
    styles,
    styleN,
    fondo_pagina,
    formatear_material,
    estilo_tabla,
)

# ==========================================================
# PDF: RESUMEN DE MATERIALES (GLOBAL)
# ==========================================================
def generar_pdf_materiales(df_mat, nombre_proy, datos_proyecto=None):

    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = [
        Paragraph(f"<b>Resumen de Materiales - Proyecto: {escape(str(nombre_proy))}</b>", styles["Title"]),
        Spacer(1, 12)
    ]

    if df_mat is None or df_mat.empty:
        elems.append(Paragraph("No se encontraron materiales.", styleN))
        doc.build(elems)
        return buffer.getvalue()

    df_agrupado = df_mat.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

    data = [["Material", "Unidad", "Cantidad"]]

    for _, row in df_agrupado.iterrows():
        data.append([
            Paragraph(formatear_material(row["Materiales"]), styleN),
            escape(str(row["Unidad"])),
            f"{float(row['Cantidad']):.2f}"
        ])

    tabla = Table(data, colWidths=[4 * inch, 1 * inch, 1 * inch])
    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
    ]))

    elems.append(tabla)
    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ==========================================================
# PDF: RESUMEN DE ESTRUCTURAS (GLOBAL)
# ==========================================================
def generar_pdf_estructuras_global(df_estructuras, nombre_proy, base_datos=None):

    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    def _safe(texto):
        return escape("" if pd.isna(texto) else str(texto))

    elems = [
        Paragraph(f"<b>Resumen de Estructuras - Proyecto: {escape(str(nombre_proy))}</b>", styles["Title"]),
        Spacer(1, 10)
    ]

    if df_estructuras is None or df_estructuras.empty:
        elems.append(Paragraph("No se encontraron estructuras.", styleN))
        doc.build(elems)
        return buffer.getvalue()

    df = df_estructuras.copy()

    # =========================================================
    # DETECCIÓN DE COLUMNA
    # =========================================================
    col_codigo = "codigodeestructura" if "codigodeestructura" in df.columns else "Estructura"

    df[col_codigo] = (
        df[col_codigo]
        .astype(str)
        .str.replace("■", "")
        .str.strip()
        .str.upper()
    )

    # =========================================================
    # 🔥 DESCRIPCIÓN DESDE INDICE (CORRECTO)
    # =========================================================
    if base_datos and "indice" in base_datos:

        df_indice = base_datos["indice"]

        if isinstance(df_indice, pd.DataFrame):

            df_indice["Código de Estructura"] = (
                df_indice["Código de Estructura"]
                .astype(str)
                .str.strip()
                .str.upper()
            )

            mapa_desc = dict(zip(
                df_indice["Código de Estructura"],
                df_indice["Descripción"]
            ))

            df["Descripcion"] = df[col_codigo].map(mapa_desc).fillna("")

    else:
        if "Descripcion" not in df.columns:
            df["Descripcion"] = ""

        df["Descripcion"] = df["Descripcion"].fillna("").astype(str)

    # =========================================================
    # AGRUPACIÓN
    # =========================================================
    if "Cantidad" not in df.columns:
        df["Cantidad"] = 1

    df = df.groupby(col_codigo, as_index=False).agg({
        "Cantidad": "sum",
        "Descripcion": "first"
    })

    # =========================================================
    # TABLA
    # =========================================================
    data = [["Estructura", "Descripción", "Cantidad"]]

    for _, r in df.iterrows():
        data.append([
            Paragraph(_safe(r[col_codigo]), styleN),
            Paragraph(_safe(r["Descripcion"]), styleN),
            Paragraph(str(int(r["Cantidad"])), styleN),
        ])

    tabla = Table(data, colWidths=[2 * inch, 3.5 * inch, 1 * inch])
    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
    ]))

    elems.append(tabla)
    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ==========================================================
# PDF: ESTRUCTURAS POR PUNTO
# ==========================================================
def generar_pdf_estructuras_por_punto(df, nombre_proy):

    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = [
        Paragraph(f"<b>Estructuras por Punto - Proyecto: {escape(str(nombre_proy))}</b>", styles["Title"]),
        Spacer(1, 12)
    ]

    if df is None or df.empty:
        elems.append(Paragraph("No hay datos.", styleN))
        doc.build(elems)
        return buffer.getvalue()

    col_codigo = "codigodeestructura" if "codigodeestructura" in df.columns else "Estructura"

    for punto, df_p in df.groupby("Punto"):

        elems.append(Paragraph(f"<b>{punto}</b>", styles["Heading2"]))

        data = [["Estructura", "Descripción", "Cantidad"]]

        for _, r in df_p.iterrows():
            data.append([
                escape(str(r.get(col_codigo, ""))),
                escape(str(r.get("Descripcion", ""))),
                escape(str(r.get("Cantidad", ""))),
            ])

        tabla = Table(data)
        tabla.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black)
        ]))

        elems.append(tabla)
        elems.append(Spacer(1, 10))

    doc.build(elems)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ==========================================================
# PDF: MATERIALES POR PUNTO
# ==========================================================
def generar_pdf_materiales_por_punto(df, nombre_proy):

    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = [
        Paragraph(f"<b>Materiales por Punto - Proyecto: {escape(str(nombre_proy))}</b>", styles["Title"]),
        Spacer(1, 12)
    ]

    if df is None or df.empty:
        elems.append(Paragraph("No hay materiales.", styleN))
        doc.build(elems)
        return buffer.getvalue()

    for punto, df_p in df.groupby("Punto"):

        elems.append(Paragraph(f"<b>{punto}</b>", styles["Heading2"]))

        df_agr = df_p.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

        data = [["Material", "Unidad", "Cantidad"]]

        for _, r in df_agr.iterrows():
            data.append([
                Paragraph(formatear_material(r["Materiales"]), styleN),
                escape(str(r["Unidad"])),
                f"{float(r['Cantidad']):.2f}",
            ])

        tabla = Table(data)
        tabla.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black)
        ]))

        elems.append(tabla)
        elems.append(Spacer(1, 10))

    doc.build(elems)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
