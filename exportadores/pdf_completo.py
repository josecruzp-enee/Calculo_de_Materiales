# -*- coding: utf-8 -*-
"""
exportadores/pdf_completo.py
PDF PROFESIONAL FINAL (CON COTIZACIÓN INTEGRADA)
"""

import re
from io import BytesIO

from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors

from exportadores.hoja_info import hoja_info_proyecto

from exportadores.pdf_base import (
    styles, styleN, styleH,
    fondo_pagina,
    extender_flowables, quitar_saltos_finales,
    formatear_material,
    _calibres_por_tipo,
)

from exportadores.pdf_reportes_simples import _tabla_estructuras_por_punto
from exportadores.pdf_anexos_costos import tabla_costos_materiales_pdf

# 🔥 NUEVO (COTIZACIÓN)
from exportadores.seccion_presupuesto import generar_seccion_presupuesto


# ==========================================================
# VALIDACIÓN
# ==========================================================
def _validar_columnas(df, requeridas, nombre):
    if df is None:
        raise ValueError(f"{nombre} es None")

    faltantes = [c for c in requeridas if c not in df.columns]
    if faltantes:
        raise ValueError(f"{nombre} no tiene columnas: {faltantes}")


# ==========================================================
# COSTOS MATERIALES
# ==========================================================
def _seccion_costos_materiales(df_costos):

    elems = [PageBreak()]
    elems.append(Paragraph("<b>4. COSTOS DE MATERIALES</b>", styles["Heading2"]))
    elems.append(Spacer(1, 0.3 * inch))

    if df_costos is None or df_costos.empty:
        elems.append(Paragraph("No hay costos de materiales.", styleN))
        return elems

    elems += tabla_costos_materiales_pdf(df_costos)

    return elems


# ==========================================================
# PDF PRINCIPAL
# ==========================================================
def generar_pdf_completo(
    df_mat,
    df_estructuras,
    df_estructuras_por_punto,
    df_mat_por_punto,
    datos_proyecto,
    df_costos=None,
    df_costos_por_punto=None,
):

    buffer, doc, elems = _crear_documento(datos_proyecto)

    # =====================================================
    # 1. INFO
    # =====================================================
    elems += _seccion_info(datos_proyecto, df_estructuras, df_mat)

    # =====================================================
    # 2. ESTRUCTURAS
    # =====================================================
    elems += _seccion_estructuras_global(doc, df_estructuras)

    # =====================================================
    # 3. MATERIALES
    # =====================================================
    elems += _seccion_materiales_global(doc, df_mat)

    # =====================================================
    # 4. COSTOS INTERNOS
    # =====================================================
    elems += _seccion_costos_materiales(df_costos)

    # =====================================================
    # 🔥 5. PRESUPUESTO (CLIENTE)
    # =====================================================
    if df_costos_por_punto is not None:
        elems += generar_seccion_presupuesto(
            doc,
            styles,
            {"df_costos_por_punto": df_costos_por_punto}
        )

    # =====================================================
    # 6. ESTRUCTURAS POR PUNTO
    # =====================================================
    elems += _seccion_estructuras_por_punto(doc, df_estructuras_por_punto)

    # =====================================================
    # 7. MATERIALES POR PUNTO
    # =====================================================
    elems += _seccion_materiales_por_punto(doc, df_mat_por_punto)

    quitar_saltos_finales(elems)
    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes


# ==========================================================
# BASE DOCUMENTO
# ==========================================================
def _crear_documento(datos_proyecto):

    buffer = BytesIO()

    doc = BaseDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=60,
        rightMargin=60,
        topMargin=160,
        bottomMargin=50
    )

    doc.membrete_pdf = datos_proyecto.get("membrete_pdf", "SMART")

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)

    template = PageTemplate(
        id="fondo",
        frames=[frame],
        onPage=fondo_pagina
    )

    doc.addPageTemplates([template])

    return buffer, doc, []


# ==========================================================
# INFO
# ==========================================================
def _seccion_info(datos_proyecto, df_estructuras, df_mat):

    return extender_flowables(
        [],
        hoja_info_proyecto(
            datos_proyecto,
            df_estructuras,
            df_mat,
            styleN=styleN,
            styleH=styleH,
            _calibres_por_tipo=_calibres_por_tipo
        )
    )


# ==========================================================
# ESTRUCTURAS
# ==========================================================
def _seccion_estructuras_global(doc, df):

    elems = [PageBreak()]
    elems.append(Paragraph("<b>2. LISTA DE ESTRUCTURAS</b>", styles["Heading2"]))
    elems.append(Spacer(1, 0.3 * inch))

    if df is None or df.empty:
        elems.append(Paragraph("No hay estructuras.", styleN))
        return elems

    import pandas as pd

    col_est = next((c for c in df.columns if "estruct" in c.lower()), None)
    col_cant = next((c for c in df.columns if "cant" in c.lower()), None)

    if col_est is None:
        raise ValueError("No se encontró columna de estructuras")

    df_fix = pd.DataFrame({
        "Estructura": df[col_est],
        "Descripción": df[col_est],
        "Cantidad": df[col_cant] if col_cant else 1
    })

    elems.append(_tabla_estructuras_por_punto("GLOBAL", df_fix, doc.width))
    return elems


# ==========================================================
# MATERIALES
# ==========================================================
def _seccion_materiales_global(doc, df_mat):

    elems = [PageBreak()]
    elems.append(Paragraph("<b>3. LISTA DE MATERIALES</b>", styles["Heading2"]))
    elems.append(Spacer(1, 0.3 * inch))

    _validar_columnas(df_mat, ["Materiales", "Unidad", "Cantidad"], "materiales_global")

    df_agr = df_mat.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

    data = [["Material", "Unidad", "Cantidad"]]

    for _, r in df_agr.iterrows():
        data.append([
            Paragraph(formatear_material(r["Materiales"]), styleN),
            r["Unidad"],
            f"{float(r['Cantidad']):,.2f}",
        ])

    tabla = Table(data, colWidths=[doc.width * 0.65, doc.width * 0.15, doc.width * 0.20])
    tabla.setStyle(TableStyle([
        ("LINEBELOW", (0,0), (-1,0), 1.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#EAEAEA")),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
    ]))

    elems.append(tabla)
    return elems


# ==========================================================
# DETALLE POR PUNTO
# ==========================================================
def _seccion_estructuras_por_punto(doc, df):

    _validar_columnas(df, ["Punto"], "estructuras_por_punto")

    elems = [PageBreak()]
    elems.append(Paragraph("<b>6. DETALLE POR PUNTO</b>", styles["Heading2"]))
    elems.append(Spacer(1, 0.3 * inch))

    for p in sorted(df["Punto"].unique()):

        match = re.search(r"\d+", str(p))
        num = match.group() if match else str(p)

        elems.append(Paragraph(f"<b>Punto {num}</b>", styles["Heading3"]))

        df_p = df[df["Punto"] == p]
        elems.append(_tabla_estructuras_por_punto(num, df_p, doc.width))
        elems.append(Spacer(1, 0.2 * inch))

    return elems


# ==========================================================
# MATERIALES POR PUNTO
# ==========================================================
def _seccion_materiales_por_punto(doc, df):

    _validar_columnas(df, ["Punto", "Materiales", "Unidad", "Cantidad"], "materiales_por_punto")

    elems = [PageBreak()]
    elems.append(Paragraph("<b>7. MATERIALES POR PUNTO</b>", styles["Heading2"]))
    elems.append(Spacer(1, 0.3 * inch))

    for p in sorted(df["Punto"].unique()):

        match = re.search(r"\d+", str(p))
        num = match.group() if match else str(p)

        elems.append(Paragraph(f"<b>Punto {num}</b>", styles["Heading3"]))

        df_p = df[df["Punto"] == p]
        df_agr = df_p.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

        data = [["Material", "Unidad", "Cantidad"]]

        for _, r in df_agr.iterrows():
            data.append([
                Paragraph(formatear_material(r["Materiales"]), styleN),
                r["Unidad"],
                f"{float(r['Cantidad']):,.2f}",
            ])

        tabla = Table(data, colWidths=[doc.width * 0.65, doc.width * 0.15, doc.width * 0.20])
        tabla.setStyle(TableStyle([
            ("LINEBELOW", (0,0), (-1,0), 1.5, colors.black),
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#EAEAEA")),
            ("ALIGN", (1,1), (-1,-1), "RIGHT"),
        ]))

        elems.append(tabla)
        elems.append(Spacer(1, 0.3 * inch))

    return elems
