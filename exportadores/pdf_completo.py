# -*- coding: utf-8 -*-
from __future__ import annotations
from exportadores.tu_archivo_cotizacion import generar_seccion_cotizacion_final
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, PageBreak
)

from exportadores.hoja_info import seccion_hoja_info
from exportadores.precios_estructura_pdf import (
    generar_tabla_precios_estructura,
    generar_cotizacion_desde_estructuras
)

from io import BytesIO
from reportlab.lib.pagesizes import letter
from exportadores.pdf_base import styles, fondo_pagina

import streamlit as st


def _log(msg):
    if "debug_pdf" not in st.session_state:
        st.session_state["debug_pdf"] = []
    st.session_state["debug_pdf"].append(msg)


def generar_pdf_completo(
    df_materiales,
    df_estructuras,
    df_precios_estructura,
    datos_proyecto,
):

    _log("📄 INICIO PDF COMPLETO")

    _log(f"df_materiales: {None if df_materiales is None else df_materiales.shape}")
    _log(f"df_estructuras: {None if df_estructuras is None else df_estructuras.shape}")
    _log(f"df_precios: {None if df_precios_estructura is None else df_precios_estructura.shape}")

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
    # HOJA INFO
    # =====================================================
    bloque_info = seccion_hoja_info(
        datos_proyecto=datos_proyecto,
        df_estructuras=df_estructuras,
        df_mat=df_materiales
    )

    _log(f"HOJA INFO elems: {len(bloque_info)}")

    elems.extend(bloque_info)
    elems.append(PageBreak())

    # =====================================================
    # PRESUPUESTO
    # =====================================================
    elems.append(Paragraph("PRESUPUESTO DE ESTRUCTURAS", styles["Heading1"]))
    elems.append(Spacer(1, 10))

    bloque_pres = generar_tabla_precios_estructura(
        df_precios_estructura,
        df_estructuras
    )

    _log(f"PRESUPUESTO elems: {len(bloque_pres)}")

    elems.extend(bloque_pres)
    elems.append(PageBreak())

    # =====================================================
    # COTIZACION
    # =====================================================
    elems.append(Paragraph("COTIZACIÓN DEL PROYECTO", styles["Heading1"]))
    elems.append(Spacer(1, 10))

    bloque_cot = generar_seccion_cotizacion_final(
        doc,
        styles,
        df_precios_estructura
    )

    _log(f"COTIZACION elems: {len(bloque_cot)}")

    # 🔥 DETECTOR
    for i, e in enumerate(bloque_cot):
        try:
            if hasattr(e, "getPlainText"):
                txt = e.getPlainText().upper()
                if "MATERIALES" in txt:
                    _log(f"🔥 TEXTO SOSPECHOSO EN COTIZACION [{i}]: {txt}")
        except:
            pass

    elems.extend(bloque_cot)

    # =====================================================
    # RESUMEN FINAL
    # =====================================================
    _log(f"TOTAL elems PDF: {len(elems)}")

    # =====================================================
    # BUILD
    # =====================================================
    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    _log("✅ PDF GENERADO")

    return pdf_bytes
