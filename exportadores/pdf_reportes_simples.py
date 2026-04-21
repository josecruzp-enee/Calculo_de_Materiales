# -*- coding: utf-8 -*-
"""
exportadores/pdf_reportes_simples.py
Reportes PDF unitarios: materiales/estructuras global y por punto.
Autor: José Nikol Cruz
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

from ayuda.debug import debug_guardar


# ==========================================================
# DEBUG INDICE
# ==========================================================
def _debug_indice(base_datos):
    """
    DEBUG:
    -------
    - Verifica si existe la hoja INDICE
    - Muestra columnas y preview
    """
    df_indice = base_datos.get("INDICE")

    debug_guardar("PDF", "INDICE_EXISTE", df_indice is not None)

    if isinstance(df_indice, pd.DataFrame):
        debug_guardar("PDF", "INDICE_COLUMNAS", list(df_indice.columns))
        debug_guardar("PDF", "INDICE_PREVIEW", df_indice.head(3))


# ==========================================================
# HEADER
# ==========================================================
def _header(titulo, nombre_proy):
    """
    SALIDA:
    -------
    Lista de elementos PDF (Paragraph + Spacer)
    """
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
# PDF: MATERIALES GLOBAL
# ==========================================================
def generar_pdf_materiales(df_mat, nombre_proy, datos_proyecto=None):
    """
    SALIDA:
    -------
    bytes (PDF)
    """

    debug_guardar("PDF", "MATERIALES_GLOBAL_IN", df_mat.shape if isinstance(df_mat, pd.DataFrame) else None)

    nombre_proy = nombre_proyecto_seguro(nombre_proy, datos_proyecto)

    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = _header("RESUMEN DE MATERIALES", nombre_proy)

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

    tabla = Table(data, colWidths=[4 * inch, 1 * inch, 1 * inch], repeatRows=1)
    tabla.setStyle(estilo_tabla())

    elems.append(tabla)
    doc.build(elems)

    debug_guardar("PDF", "MATERIALES_GLOBAL_OUT_FILAS", len(df_agrupado))

    return buffer.getvalue()


# ==========================================================
# PDF: ESTRUCTURAS GLOBAL
# ==========================================================
def generar_pdf_estructuras_global(df_estructuras, nombre_proy, base_datos=None, datos_proyecto=None):
    """
    SALIDA:
    -------
    bytes (PDF)
    """

    debug_guardar("PDF", "ESTRUCTURAS_GLOBAL_IN", df_estructuras.shape if isinstance(df_estructuras, pd.DataFrame) else None)

    nombre_proy = nombre_proyecto_seguro(nombre_proy, datos_proyecto)

    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = _header("RESUMEN DE ESTRUCTURAS", nombre_proy)

    if df_estructuras is None or df_estructuras.empty:
        elems.append(Paragraph("No se encontraron estructuras.", styleN))
        doc.build(elems)
        return buffer.getvalue()

    df = df_estructuras.copy()

    col_codigo = "CODIGO" if "CODIGO" in df.columns else "Estructura"

    df[col_codigo] = df[col_codigo].astype(str).str.strip().str.upper()

    _debug_indice(base_datos)

    if base_datos:
        df_indice = base_datos.get("INDICE") or base_datos.get("indice")

        if isinstance(df_indice, pd.DataFrame):

            df_indice = df_indice.copy()
            df_indice.columns = [str(c).strip().upper() for c in df_indice.columns]

            if "CODIGO" in df_indice.columns:

                df_indice["CODIGO"] = df_indice["CODIGO"].astype(str).str.strip().str.upper()

                mapa_desc = dict(zip(
                    df_indice["CODIGO"],
                    df_indice.get("DESCRIPCION", "")
                ))

                df["Descripcion"] = df[col_codigo].map(mapa_desc).fillna("")

    if "Cantidad" not in df.columns:
        df["Cantidad"] = 1

    df = df.groupby(col_codigo, as_index=False).agg({
        "Cantidad": "sum",
        "Descripcion": "first"
    })

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

    debug_guardar("PDF", "ESTRUCTURAS_GLOBAL_OUT_FILAS", len(df))

    return buffer.getvalue()


# ==========================================================
# PDF: ESTRUCTURAS POR PUNTO
# ==========================================================
def generar_pdf_estructuras_por_punto(df, nombre_proy, datos_proyecto=None):
    """
    SALIDA:
    -------
    bytes (PDF)
    """

    debug_guardar("PDF", "ESTRUCTURAS_POR_PUNTO_IN", df.shape if isinstance(df, pd.DataFrame) else None)

    nombre_proy = nombre_proyecto_seguro(nombre_proy, datos_proyecto)

    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = _header("ESTRUCTURAS POR PUNTO", nombre_proy)

    if df is None or df.empty:
        elems.append(Paragraph("No hay datos.", styleN))
        doc.build(elems)
        return buffer.getvalue()

    col_codigo = "CODIGO" if "CODIGO" in df.columns else "Estructura"

    for punto, df_p in df.groupby("Punto"):
        elems.append(Paragraph(f"<b>{punto}</b>", styles["Heading2"]))

        data = [["Estructura", "Descripción", "Cantidad"]]

        for _, r in df_p.iterrows():
            data.append([
                escape(str(r.get(col_codigo, ""))),
                escape(str(r.get("Descripcion", ""))),
                escape(str(r.get("Cantidad", ""))),
            ])

        tabla = Table(data, colWidths=[doc.width*0.18, doc.width*0.67, doc.width*0.15], repeatRows=1)
        tabla.setStyle(estilo_tabla())

        elems.append(tabla)
        elems.append(Spacer(1, 10))

    doc.build(elems)

    return buffer.getvalue()


# ==========================================================
# PDF: MATERIALES POR PUNTO (FALTANTE)
# ==========================================================
def generar_pdf_materiales_por_punto(df, nombre_proy, datos_proyecto=None):
    """
    SALIDA:
    -------
    bytes (PDF)
    """

    debug_guardar("PDF", "MATERIALES_POR_PUNTO_IN", df.shape if isinstance(df, pd.DataFrame) else None)

    nombre_proy = nombre_proyecto_seguro(nombre_proy, datos_proyecto)

    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = _header("MATERIALES POR PUNTO", nombre_proy)

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

        tabla = Table(data, colWidths=[doc.width*0.55, doc.width*0.20, doc.width*0.25], repeatRows=1)
        tabla.setStyle(estilo_tabla())

        elems.append(tabla)
        elems.append(Spacer(1, 10))

    doc.build(elems)

    return buffer.getvalue()
