# -*- coding: utf-8 -*-
"""
exportadores/pdf_reportes_simples.py
FIX: normalización fuerte de códigos + DEBUG INTEGRADO (sin cambiar lógica)
"""

from __future__ import annotations

import pandas as pd
import re
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
# NORMALIZACIÓN
# ==========================================================
def limpiar_codigo_fuerte(x):
    if pd.isna(x):
        return ""
    x = str(x).upper().strip()
    x = re.sub(r"\(.*?\)", "", x)
    x = x.replace("■", "")
    x = x.replace("\n", "").replace("\r", "")
    return x.strip()


# ==========================================================
# HEADER
# ==========================================================
def _header(titulo, nombre_proy):

    styleTitulo = styles["Title"].clone("titulo_center")
    styleTitulo.alignment = TA_CENTER

    styleProyecto = styles["Normal"].clone("proyecto_center")
    styleProyecto.alignment = TA_CENTER

    return [
        Paragraph(titulo, styleTitulo),
        Spacer(1, 6),
        Paragraph(f"<b>Proyecto:</b> {escape(str(nombre_proy))}", styleProyecto),
        Spacer(1, 12),
    ]


# ==========================================================
# MATERIAL GLOBAL (SIN CAMBIOS)
# ==========================================================
def generar_pdf_materiales(df_mat, nombre_proy, datos_proyecto=None):

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

    df_agr = df_mat.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

    data = [["Material", "Unidad", "Cantidad"]]

    for _, r in df_agr.iterrows():
        data.append([
            Paragraph(formatear_material(r["Materiales"]), styleN),
            escape(str(r["Unidad"])),
            f"{float(r['Cantidad']):.2f}"
        ])

    tabla = Table(data)
    tabla.setStyle(estilo_tabla())

    elems.append(tabla)
    doc.build(elems)

    return buffer.getvalue()


# ==========================================================
# 🔥 GLOBAL CON DEBUG INTEGRADO (SIN CAMBIAR LÓGICA)
# ==========================================================
def generar_pdf_estructuras_global(df_estructuras, nombre_proy, base_datos=None, datos_proyecto=None):

    nombre_proy = nombre_proyecto_seguro(nombre_proy, datos_proyecto)

    debug = {}

    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = _header("RESUMEN DE ESTRUCTURAS", nombre_proy)

    if df_estructuras is None or df_estructuras.empty:
        debug["error"] = "df_estructuras vacío"
        elems.append(Paragraph("No se encontraron estructuras.", styleN))
        doc.build(elems)
        return buffer.getvalue(), debug

    df = df_estructuras.copy()

    col_codigo = "codigodeestructura" if "codigodeestructura" in df.columns else "Estructura"

    df[col_codigo] = df[col_codigo].apply(limpiar_codigo_fuerte)

    # =========================
    # DEBUG INPUT DF
    # =========================
    debug["df_columns"] = list(df.columns)
    debug["df_sample"] = df[col_codigo].astype(str).head(10).tolist()
    debug["col_codigo"] = col_codigo

    # =========================
    # MAPEO (SIN CAMBIAR LÓGICA)
    # =========================
    if base_datos and "indice" in base_datos:

        df_indice = base_datos["indice"].copy()

        debug["indice_columns"] = list(df_indice.columns)
        debug["indice_sample"] = df_indice["codigodeestructura"].astype(str).head(10).tolist()

        df_indice["codigodeestructura"] = df_indice["codigodeestructura"].apply(limpiar_codigo_fuerte)

        mapa_desc = dict(zip(
            df_indice["codigodeestructura"],
            df_indice["Descripcion"]
        ))

        debug["mapa_size"] = len(mapa_desc)

        debug["match_test"] = [
            (x, x in mapa_desc)
            for x in df[col_codigo].astype(str).head(10)
        ]

        df["Descripcion"] = df[col_codigo].map(mapa_desc).fillna("")

    else:
        df["Descripcion"] = ""
        debug["error"] = "NO base_datos o NO indice"

    # =========================
    # AGRUPACIÓN
    # =========================
    if "Cantidad" not in df.columns:
        df["Cantidad"] = 1

    df = df.groupby(col_codigo, as_index=False).agg({
        "Cantidad": "sum",
        "Descripcion": "first"
    })

    # =========================
    # OUTPUT PDF
    # =========================
    data = [["Estructura", "Descripción", "Cantidad"]]

    for _, r in df.iterrows():
        data.append([
            Paragraph(escape(str(r[col_codigo])), styleN),
            Paragraph(escape(str(r["Descripcion"])), styleN),
            Paragraph(str(int(r["Cantidad"])), styleN),
        ])

    tabla = Table(data)
    tabla.setStyle(estilo_tabla())

    elems.append(tabla)
    doc.build(elems)

    return buffer.getvalue(), debug


# ==========================================================
# POR PUNTO (DEBUG INTEGRADO)
# ==========================================================
def generar_pdf_estructuras_por_punto(df, nombre_proy, base_datos=None, datos_proyecto=None):

    nombre_proy = nombre_proyecto_seguro(nombre_proy, datos_proyecto)

    debug = {}

    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = _header("ESTRUCTURAS POR PUNTO", nombre_proy)

    if df is None or df.empty:
        debug["error"] = "df vacío"
        elems.append(Paragraph("No hay datos.", styleN))
        doc.build(elems)
        return buffer.getvalue(), debug

    df = df.copy()

    col_codigo = "codigodeestructura" if "codigodeestructura" in df.columns else "Estructura"

    df[col_codigo] = df[col_codigo].apply(limpiar_codigo_fuerte)

    debug["df_sample"] = df[col_codigo].astype(str).head(10).tolist()

    if base_datos and "indice" in base_datos:

        df_indice = base_datos["indice"].copy()

        df_indice["codigodeestructura"] = df_indice["codigodeestructura"].apply(limpiar_codigo_fuerte)

        mapa_desc = dict(zip(
            df_indice["codigodeestructura"],
            df_indice["Descripcion"]
        ))

        debug["mapa_size"] = len(mapa_desc)

        debug["match_test"] = [
            x in mapa_desc
            for x in df[col_codigo].astype(str).head(10)
        ]

        df["Descripcion"] = df[col_codigo].map(mapa_desc).fillna("")
    else:
        df["Descripcion"] = ""
        debug["error"] = "NO indice"

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
        tabla.setStyle(estilo_tabla())

        elems.append(tabla)

    doc.build(elems)

    return buffer.getvalue(), debug


# ==========================================================
# MATERIALES POR PUNTO (SIN DEBUG)
# ==========================================================
def generar_pdf_materiales_por_punto(df, nombre_proy, datos_proyecto=None):

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

        tabla = Table(data)
        tabla.setStyle(estilo_tabla())

        elems.append(tabla)

    doc.build(elems)

    return buffer.getvalue()
