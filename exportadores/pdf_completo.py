# -*- coding: utf-8 -*-
from io import BytesIO

from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, PageBreak
)
from reportlab.lib.pagesizes import letter

from exportadores.pdf_base import styles, fondo_pagina
from exportadores.cotizacion import generar_seccion_presupuesto


def generar_pdf_completo(
    df_materiales,
    df_estructuras,
    df_mat_por_punto,
    df_costos_por_punto,
    df_costos_estructura,
    datos_proyecto,
):

    import streamlit as st

    st.write("DEBUG PDF COMPLETO")

    st.write("df_materiales:", df_materiales.shape if df_materiales is not None else None)
    st.write("df_estructuras:", df_estructuras.shape if df_estructuras is not None else None)
    st.write("df_mat_por_punto:", df_mat_por_punto.shape if df_mat_por_punto is not None else None)
    st.write("df_costos_por_punto:", df_costos_por_punto.shape if df_costos_por_punto is not None else None)
    
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
    # PORTADA / INFO
    # =====================================================
    elems.append(Paragraph("<b>REPORTE DE PROYECTO</b>", styles["Heading1"]))
    elems.append(Spacer(1, 12))

    # =====================================================
    # 🔥 PRESUPUESTO (LO MÁS IMPORTANTE)
    # =====================================================
    from exportadores.precios_estructura import generar_tabla_costos_estructura

    if df_costos_estructura is not None:
        try:
            tabla = generar_tabla_costos_estructura(
                doc,
                styles,
                df_costos_estructura
            )
            if tabla:
                elems += tabla
        except Exception as e:
            elems.append(Paragraph(f"Error costos estructura: {str(e)}", styles["Normal"]))
    
    # =====================================================
    # FINAL
    # =====================================================
    if not elems:
        elems.append(Paragraph("Sin información disponible", styles["Normal"]))
    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
