# -*- coding: utf-8 -*-
from __future__ import annotations

from exportadores.cotizacion import generar_seccion_cotizacion_final

from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, PageBreak
)

from exportadores.hoja_info import seccion_hoja_info
from exportadores.precios_estructura_pdf import generar_tabla_precios_estructura

# 🔥 IMPORTANTE
from exportadores.reporte_costos_proyecto import construir_bloque_costos

import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import letter
from exportadores.pdf_base import styles, fondo_pagina

import streamlit as st


# =========================================================
# DEBUG
# =========================================================
def _log(msg):
    if "debug_pdf" not in st.session_state:
        st.session_state["debug_pdf"] = []
    st.session_state["debug_pdf"].append(msg)


# =========================================================
# PDF COMPLETO
# =========================================================
def generar_pdf_completo(
    df_materiales,
    df_estructuras,
    df_precios_estructura,
    datos_proyecto,
    costos=None   # 🔥 CAMBIO IMPORTANTE
):

    _log("📄 INICIO PDF COMPLETO")

    buffer = BytesIO()

    doc = BaseDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=60,
        rightMargin=60,
        topMargin=120,
        bottomMargin=50
    )

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)

    template = PageTemplate(
        id="normal",
        frames=[frame],
        onPage=fondo_pagina
    )

    doc.addPageTemplates([template])

    elems = []

    # =====================================================
    # 1. HOJA INFO
    # =====================================================
    elems.extend(seccion_hoja_info(
        datos_proyecto=datos_proyecto,
        df_estructuras=df_estructuras,
        df_mat=df_materiales,
        doc_width=doc.width
    ))

    elems.append(PageBreak())

    # =====================================================
    # 2. PRESUPUESTO
    # =====================================================
    elems.append(Paragraph("PRESUPUESTO DE ESTRUCTURAS", styles["Heading1"]))
    elems.append(Spacer(1, 10))

    if isinstance(df_precios_estructura, pd.DataFrame) and not df_precios_estructura.empty:

        elems.extend(generar_tabla_precios_estructura(
            df_precios_estructura,
            df_estructuras
        ))

    else:
        elems.append(Paragraph(
            "No se dispone de información de precios de estructuras.",
            styles["Normal"]
        ))

    elems.append(PageBreak())

    # =====================================================
    # 3. COTIZACIÓN
    # =====================================================
    if isinstance(df_precios_estructura, pd.DataFrame) and not df_precios_estructura.empty:

        df_tmp = df_precios_estructura.copy()

        if "Subtotal" not in df_tmp.columns:
            df_tmp["Subtotal"] = df_tmp["Precio Unitario"] * df_tmp["Cantidad"]

        elems.extend(generar_seccion_cotizacion_final(doc, styles, df_tmp))

    else:
        elems.append(Paragraph(
            "No se puede generar la cotización por falta de precios.",
            styles["Normal"]
        ))

    # =====================================================
    # 4. COSTOS DE PROYECTO (CORREGIDO 🔥)
    # =====================================================
    elems.append(PageBreak())

    elems.append(Paragraph("COSTOS DE PROYECTO", styles["Heading1"]))
    elems.append(Spacer(1, 10))

    if not costos or not costos.get("ok"):

        elems.append(Paragraph(
            "No se dispone del cálculo de costos de proyecto.",
            styles["Normal"]
        ))

    else:

        construir_bloque_costos(
            elems,
            styles,
            costos.get("resultado_costos_proyecto"),   # ✔ correcto
            costos.get("df_materiales_costos")         # 🔥 CLAVE
        )

    # =====================================================
    # BUILD
    # =====================================================
    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    _log("✅ PDF GENERADO")

    return pdf_bytes
