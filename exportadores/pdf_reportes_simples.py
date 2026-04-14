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
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER

from exportadores.pdf_base import styles, styleN, fondo_pagina, formatear_material


# ==========================================================
# PDF: RESUMEN DE MATERIALES (GLOBAL)
# ==========================================================
def generar_pdf_materiales(df_mat, nombre_proy, datos_proyecto=None):
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
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
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
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
    doc = BaseDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=50,
        rightMargin=50,
        topMargin=70,
        bottomMargin=40
    )

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    def _safe_para(texto):
        t = "" if pd.isna(texto) else str(texto)
        t = escape(t)
        t = t.replace("■", "")
        return t

    elems = [
        Paragraph(f"<b>Resumen de Estructuras - Proyecto: {escape(str(nombre_proy))}</b>", styles["Title"]),
        Spacer(1, 8)
    ]

    if df_estructuras is None or df_estructuras.empty:
        elems.append(Paragraph("No se encontraron estructuras.", styleN))
        doc.build(elems)
        return buffer.getvalue()

    df = df_estructuras.copy()

    # =========================================================
    # LIMPIEZA
    # =========================================================
    df["codigodeestructura"] = (
        df["codigodeestructura"]
        .astype(str)
        .str.replace("■", "")
        .str.strip()
    )

    # =========================================================
    # 🔥 RECONSTRUCCIÓN DESCRIPCIÓN DESDE BASE
    # =========================================================
    if ("Descripcion" not in df.columns or df["Descripcion"].isna().all()) and base_datos:

        mapa_desc = {}

        for nombre_estructura, df_mat in base_datos.items():

            if isinstance(df_mat, pd.DataFrame) and "Descripcion" in df_mat.columns:
                desc = df_mat["Descripcion"].dropna().astype(str).unique()

                if len(desc) > 0:
                    mapa_desc[nombre_estructura.strip()] = desc[0]

        df["Descripcion"] = df["codigodeestructura"].map(mapa_desc).fillna("")

    else:
        df["Descripcion"] = df.get("Descripcion", "").fillna("").astype(str)

    # =========================================================
    # AGRUPACIÓN
    # =========================================================
    df = df.groupby("codigodeestructura", as_index=False).agg({
        "Cantidad": "sum",
        "Descripcion": "first"
    })

    # =========================================================
    # TABLA
    # =========================================================
    ancho = doc.width * 0.95

    data = [[
        Paragraph("Estructura", styles["Normal"]),
        Paragraph("Descripción", styles["Normal"]),
        Paragraph("Cantidad", styles["Normal"]),
    ]]

    for _, r in df.iterrows():
        data.append([
            Paragraph(_safe_para(r["codigodeestructura"]), styles["Normal"]),
            Paragraph(_safe_para(r["Descripcion"]), styles["Normal"]),
            Paragraph(str(int(r["Cantidad"])), styles["Normal"]),
        ])

    tabla = Table(
        data,
        colWidths=[ancho * 0.25, ancho * 0.55, ancho * 0.20],
        repeatRows=1,
        hAlign="CENTER"
    )

    elems.append(tabla)
    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

# ==========================================================
# PDF: ESTRUCTURAS POR PUNTO
# ==========================================================
def generar_pdf_estructuras_por_punto(df_por_punto, nombre_proy):
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = [
        Paragraph(f"<b>Estructuras por Punto - Proyecto: {escape(str(nombre_proy))}</b>", styles["Title"]),
        Spacer(1, 12)
    ]

    if df_por_punto is None or df_por_punto.empty:
        elems.append(Paragraph("No se encontraron estructuras por punto.", styleN))
        doc.build(elems)
        return buffer.getvalue()

    puntos = sorted(
        df_por_punto["Punto"].unique(),
        key=lambda x: int(re.sub(r"\D", "", str(x)) or 0)
    )

    for p in puntos:
        m = re.search(r"(\d+)", str(p))
        num = m.group(1) if m else str(p)

        elems.append(Spacer(1, 6))
        elems.append(Paragraph(f"<b>Punto {escape(num)}</b>", styles["Heading2"]))

        df_p = df_por_punto[df_por_punto["Punto"] == p]

        data = [["Estructura", "Descripción", "Cantidad"]]
        for _, r in df_p.iterrows():
            data.append([
                escape(str(r.get("codigodeestructura", ""))),
                escape(str(r.get("Descripcion", ""))),
                escape(str(r.get("Cantidad", ""))),
            ])

        tabla = Table(data, colWidths=[1.5 * inch, 4 * inch, 1 * inch])
        tabla.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
            ("ALIGN", (2, 1), (2, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))

        elems.append(tabla)
        elems.append(Spacer(1, 0.2 * inch))

    doc.build(elems)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ==========================================================
# TABLA: ESTRUCTURAS POR PUNTO (USADA EN PDF COMPLETO)
# ==========================================================
def _tabla_estructuras_por_punto(punto, df_p, doc_width):
    st_hdr = ParagraphStyle("hdr", parent=styles["Normal"], fontName="Helvetica-Bold",
                            fontSize=9, alignment=TA_CENTER)
    st_code = ParagraphStyle("code", parent=styles["Normal"], fontSize=8)
    st_desc = ParagraphStyle("desc", parent=styles["Normal"], fontSize=8, wordWrap="CJK")
    st_desc.splitLongWords = 1
    st_qty = ParagraphStyle("qty", parent=styles["Normal"], fontSize=8, alignment=TA_CENTER)

    data = [[
        Paragraph("Estructura", st_hdr),
        Paragraph("Descripción", st_hdr),
        Paragraph("Cantidad", st_hdr)
    ]]

    for _, r in df_p.iterrows():
        data.append([
            Paragraph(escape(str(r.get("codigodeestructura", ""))), st_code),
            Paragraph(escape(str(r.get("Descripcion", ""))), st_desc),
            Paragraph(escape(str(r.get("Cantidad", ""))), st_qty),
        ])

    t = Table(
        data,
        colWidths=[doc_width * 0.20, doc_width * 0.65, doc_width * 0.15],
        repeatRows=1
    )

    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    return t


# ==========================================================
# PDF: MATERIALES POR PUNTO
# ==========================================================
def generar_pdf_materiales_por_punto(df_por_punto, nombre_proy):
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = [
        Paragraph(f"<b>Materiales por Punto - Proyecto: {escape(str(nombre_proy))}</b>", styles["Title"]),
        Spacer(1, 12),
    ]

    if df_por_punto is None or df_por_punto.empty:
        elems.append(Paragraph("No se encontraron materiales por punto.", styleN))
        doc.build(elems)
        return buffer.getvalue()

    puntos = sorted(
        df_por_punto["Punto"].unique(),
        key=lambda x: int(re.search(r"\d+", str(x)).group(0)) if re.search(r"\d+", str(x)) else 0
    )

    for p in puntos:
        m = re.search(r"(\d+)", str(p))
        num = m.group(1) if m else str(p)

        elems.append(Paragraph(f"<b>Punto {escape(num)}</b>", styles["Heading2"]))

        df_p = df_por_punto[df_por_punto["Punto"] == p]
        df_agr = df_p.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

        data = [["Material", "Unidad", "Cantidad"]]
        for _, r in df_agr.iterrows():
            data.append([
                Paragraph(formatear_material(r["Materiales"]), styleN),
                escape(str(r["Unidad"])),
                f"{float(r['Cantidad']):.2f}",
            ])

        tabla = Table(data, colWidths=[4 * inch, 1 * inch, 1 * inch])
        tabla.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.darkgreen),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ]))

        elems.append(tabla)
        elems.append(Spacer(1, 0.2 * inch))

    doc.build(elems)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
