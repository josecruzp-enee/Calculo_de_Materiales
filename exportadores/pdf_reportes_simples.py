# -*- coding: utf-8 -*-
"""
exportadores/pdf_reportes_simples.py
Reportes PDF unitarios: materiales/estructuras global y por punto.
ESTILO ORIGINAL RESTAURADO
"""

import pandas as pd
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER

from exportadores.pdf_base import (
    styles,
    styleN,
    fondo_pagina,
    formatear_material,
    estilo_tabla,
    nombre_proyecto_seguro,
)


# ==========================================================
# 🎯 HEADER ESTÁNDAR (TU ESTILO ORIGINAL)
# ==========================================================
def _header(titulo, nombre_proy):

    styleTitulo = styles["Title"].clone("titulo_center")
    styleTitulo.alignment = TA_CENTER

    styleProyecto = styles["Normal"].clone("proyecto_center")
    styleProyecto.alignment = TA_CENTER
    styleProyecto.fontSize = 11
    styleProyecto.leading = 13

    return [
        Paragraph(titulo, styleTitulo),
        Spacer(1, 6),
        Paragraph(f"<b>Proyecto:</b> {escape(str(nombre_proy))}", styleProyecto),
        Spacer(1, 12),
    ]


# ==========================================================
# 🔧 DOC BASE
# ==========================================================
def _crear_doc():

    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    return doc, buffer


# ==========================================================
# 📄 MATERIALES GLOBAL
# ==========================================================
def generar_pdf_materiales(df_mat, nombre_proy, datos_proyecto=None):

    nombre_proy = nombre_proyecto_seguro(nombre_proy, datos_proyecto)
    doc, buffer = _crear_doc()

    elems = _header("RESUMEN DE MATERIALES", nombre_proy)

    if df_mat is None or df_mat.empty:
        elems.append(Paragraph("No se encontraron materiales.", styleN))
        doc.build(elems)
        return buffer.getvalue()

    df_agr = df_mat.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

    data = [["Material", "Unidad", "Cantidad"]]

    for _, r in df_agr.iterrows():
        data.append([
            Paragraph(formatear_material(r["Materiales"]), styleN),
            escape(str(r["Unidad"])),
            f"{float(r['Cantidad']):.2f}"
        ])

    tabla = Table(data, colWidths=[4 * inch, 1 * inch, 1 * inch], repeatRows=1)
    tabla.setStyle(estilo_tabla())

    elems.append(tabla)
    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ==========================================================
# 📄 ESTRUCTURAS GLOBAL
# ==========================================================
def generar_pdf_estructuras_global(df_estructuras, nombre_proy, base_datos=None, datos_proyecto=None):

    nombre_proy = nombre_proyecto_seguro(nombre_proy, datos_proyecto)
    doc, buffer = _crear_doc()

    elems = _header("RESUMEN DE ESTRUCTURAS", nombre_proy)

    if df_estructuras is None or df_estructuras.empty:
        elems.append(Paragraph("No se encontraron estructuras.", styleN))
        doc.build(elems)
        return buffer.getvalue()

    df = df_estructuras.copy()

    col_codigo = "codigodeestructura" if "codigodeestructura" in df.columns else "Estructura"

    df[col_codigo] = (
        df[col_codigo]
        .astype(str)
        .str.replace("■", "")
        .str.strip()
        .str.upper()
    )

    # ==========================================================
    # 🔥 DESCRIPCIÓN DESDE BASE DE DATOS (VERSIÓN ROBUSTA)
    # ==========================================================
    df_indice = None

    if base_datos:
        df_indice = (
            base_datos.get("indice")
            or base_datos.get("INDICE")
            or base_datos.get("Indice")
        )

    if isinstance(df_indice, pd.DataFrame):

        # Normalizar nombres de columnas
        df_indice.columns = [c.strip().upper() for c in df_indice.columns]

        col_codigo_idx = None
        col_desc_idx = None

        for c in df_indice.columns:
            if "CODIGO" in c and "ESTRUCTURA" in c:
                col_codigo_idx = c
            if "DESCRIP" in c:
                col_desc_idx = c

        if col_codigo_idx and col_desc_idx:

            mapa_desc = dict(zip(
                df_indice[col_codigo_idx].astype(str).str.strip().str.upper(),
                df_indice[col_desc_idx].astype(str).str.strip()
            ))

            df["Descripcion"] = (
                df[col_codigo]
                .astype(str)
                .str.strip()
                .str.upper()
                .map(mapa_desc)
                .fillna("")
            )
        else:
            df["Descripcion"] = ""
    else:
        df["Descripcion"] = df.get("Descripcion", "").fillna("").astype(str)

    # ==========================================================
    # AGRUPACIÓN
    # ==========================================================
    if "Cantidad" not in df.columns:
        df["Cantidad"] = 1

    df = df.groupby(col_codigo, as_index=False).agg({
        "Cantidad": "sum",
        "Descripcion": "first"
    })

    # ==========================================================
    # TABLA
    # ==========================================================
    data = [["Estructura", "Descripción", "Cantidad"]]

    for _, r in df.iterrows():
        data.append([
            Paragraph(escape(str(r[col_codigo])), styleN),
            Paragraph(escape(str(r["Descripcion"])), styleN),
            Paragraph(str(int(r["Cantidad"])), styleN),
        ])

    tabla = Table(data, colWidths=[2 * inch, 3.5 * inch, 1 * inch], repeatRows=1)
    tabla.setStyle(estilo_tabla())

    elems.append(tabla)
    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
# ==========================================================
# 📄 ESTRUCTURAS POR PUNTO
# ==========================================================
def generar_pdf_estructuras_por_punto(df, nombre_proy, datos_proyecto=None):

    nombre_proy = nombre_proyecto_seguro(nombre_proy, datos_proyecto)
    doc, buffer = _crear_doc()

    elems = _header("ESTRUCTURAS POR PUNTO", nombre_proy)

    if df is None or df.empty:
        elems.append(Paragraph("No hay datos.", styleN))
        doc.build(elems)
        return buffer.getvalue()

    col_codigo = "codigodeestructura" if "codigodeestructura" in df.columns else "Estructura"

    for punto, df_p in df.groupby("Punto"):

        elems.append(Paragraph(f"<b>{escape(str(punto))}</b>", styles["Heading2"]))

        data = [["Estructura", "Descripción", "Cantidad"]]

        for _, r in df_p.iterrows():
            data.append([
                escape(str(r.get(col_codigo, ""))),
                escape(str(r.get("Descripcion", ""))),
                escape(str(r.get("Cantidad", ""))),
            ])

        tabla = Table(
            data,
            colWidths=[doc.width * 0.18, doc.width * 0.67, doc.width * 0.15],
            repeatRows=1
        )

        tabla.setStyle(estilo_tabla())

        elems.append(tabla)
        elems.append(Spacer(1, 10))

    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ==========================================================
# 📄 MATERIALES POR PUNTO
# ==========================================================
def generar_pdf_materiales_por_punto(df, nombre_proy, datos_proyecto=None):

    nombre_proy = nombre_proyecto_seguro(nombre_proy, datos_proyecto)
    doc, buffer = _crear_doc()

    elems = _header("MATERIALES POR PUNTO", nombre_proy)

    if df is None or df.empty:
        elems.append(Paragraph("No hay materiales.", styleN))
        doc.build(elems)
        return buffer.getvalue()

    for punto, df_p in df.groupby("Punto"):

        elems.append(Paragraph(f"<b>{escape(str(punto))}</b>", styles["Heading2"]))

        df_agr = df_p.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

        data = [["Material", "Unidad", "Cantidad"]]

        for _, r in df_agr.iterrows():
            data.append([
                Paragraph(formatear_material(r["Materiales"]), styleN),
                escape(str(r["Unidad"])),
                f"{float(r['Cantidad']):.2f}",
            ])

        tabla = Table(
            data,
            colWidths=[doc.width * 0.55, doc.width * 0.20, doc.width * 0.25],
            repeatRows=1
        )

        tabla.setStyle(estilo_tabla())

        elems.append(tabla)
        elems.append(Spacer(1, 10))

    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
