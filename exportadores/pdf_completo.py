# -*- coding: utf-8 -*-
from __future__ import annotations

from exportadores.cotizacion import generar_seccion_cotizacion_final

from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, PageBreak
)

from exportadores.hoja_info import seccion_hoja_info
from exportadores.precios_estructura_pdf import generar_tabla_precios_estructura

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
):

    _log("📄 INICIO PDF COMPLETO")

    _log(f"df_materiales: {None if df_materiales is None else df_materiales.shape}")
    _log(f"df_estructuras: {None if df_estructuras is None else df_estructuras.shape}")
    _log(f"df_precios: {None if df_precios_estructura is None else df_precios_estructura}")

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
    bloque_info = seccion_hoja_info(
        datos_proyecto=datos_proyecto,
        df_estructuras=df_estructuras,
        df_mat=df_materiales
        doc_width=doc.width
    )

    elems.extend(bloque_info)
    elems.append(PageBreak())

    # =====================================================
    # 2. PRESUPUESTO
    # =====================================================
    elems.append(Paragraph("PRESUPUESTO DE ESTRUCTURAS", styles["Heading1"]))
    elems.append(Spacer(1, 10))

    if (
        df_precios_estructura is None
        or not isinstance(df_precios_estructura, pd.DataFrame)
        or df_precios_estructura.empty
    ):
        _log("⚠️ NO HAY PRECIOS")

        elems.append(Paragraph(
            "No se dispone de información de precios de estructuras.",
            styles["Normal"]
        ))

    else:
        bloque_pres = generar_tabla_precios_estructura(
            df_precios_estructura,
            df_estructuras
        )
        elems.extend(bloque_pres)

    elems.append(PageBreak())

    # =====================================================
    # 3. COTIZACIÓN
    # =====================================================
    elems.append(Paragraph("COTIZACIÓN DEL PROYECTO", styles["Heading1"]))
    elems.append(Spacer(1, 10))

    if (
        df_precios_estructura is None
        or not isinstance(df_precios_estructura, pd.DataFrame)
        or df_precios_estructura.empty
    ):
        elems.append(Paragraph(
            "No se puede generar la cotización por falta de precios.",
            styles["Normal"]
        ))

    else:
        # 🔥 COPIA SEGURA (NO MUTAR ORIGINAL)
        df_tmp = df_precios_estructura.copy()

        if "Subtotal" not in df_tmp.columns:
            df_tmp["Subtotal"] = (
                df_tmp["Precio Unitario"] *
                df_tmp["Cantidad"]
            )

        bloque_cot = generar_seccion_cotizacion_final(
            doc,
            styles,
            df_tmp
        )

        elems.extend(bloque_cot)

    # =====================================================
    # BUILD
    # =====================================================
    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    _log("✅ PDF GENERADO")

    return pdf_bytes
