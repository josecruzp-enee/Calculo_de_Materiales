# -*- coding: utf-8 -*-
from __future__ import annotations

# =====================================================
# IMPORTS
# =====================================================
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


# =====================================================
# PDF COMPLETO (DEBUG ACTIVADO 🔥)
# =====================================================
def generar_pdf_completo(
    df_materiales,
    df_estructuras,
    df_precios_estructura,
    datos_proyecto,
):

    st.write("📄 DEBUG → ENTRANDO A PDF COMPLETO")

    # =====================================================
    # DEBUG INPUTS
    # =====================================================
    st.write("df_materiales:", None if df_materiales is None else df_materiales.shape)
    st.write("df_estructuras:", None if df_estructuras is None else df_estructuras.shape)
    st.write("df_precios_estructura:", None if df_precios_estructura is None else df_precios_estructura.shape)

    if df_precios_estructura is not None:
        st.write("COLUMNAS PRECIOS:", list(df_precios_estructura.columns))
        st.write(df_precios_estructura.head())

    buffer = BytesIO()

    doc = BaseDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=60,
        rightMargin=60,
        topMargin=120,
        bottomMargin=50
    )

    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height
    )

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
    st.write("➡️ Generando HOJA INFO")

    bloque_info = seccion_hoja_info(
        datos_proyecto=datos_proyecto,
        df_estructuras=df_estructuras,
        df_mat=df_materiales
    )

    st.write("HOJA INFO elementos:", len(bloque_info))
    st.write("Tipos:", [type(x).__name__ for x in bloque_info])

    elems.extend(bloque_info)

    elems.append(PageBreak())

    # =====================================================
    # NORMALIZAR PRECIOS
    # =====================================================
    st.write("➡️ Normalizando precios")

    if df_precios_estructura is None:
        import pandas as pd
        df_precios_estructura = pd.DataFrame(columns=[
            "Estructura", "Cantidad", "Precio Unitario", "Subtotal"
        ])
        st.write("⚠️ df_precios_estructura era None")

    else:
        if "Cantidad" not in df_precios_estructura.columns:
            st.write("⚠️ Agregando columna Cantidad")

            cantidades = (
                df_estructuras.groupby("Estructura")["Cantidad"]
                .sum()
                .to_dict()
            )
            df_precios_estructura["Cantidad"] = (
                df_precios_estructura["Estructura"]
                .map(cantidades)
                .fillna(0)
            )

        if "Precio Unitario" not in df_precios_estructura.columns:
            st.write("⚠️ Agregando Precio Unitario")
            df_precios_estructura["Precio Unitario"] = 0

        if "Subtotal" not in df_precios_estructura.columns:
            st.write("⚠️ Calculando Subtotal")
            df_precios_estructura["Subtotal"] = (
                df_precios_estructura["Precio Unitario"] *
                df_precios_estructura["Cantidad"]
            )

    # =====================================================
    # PRESUPUESTO
    # =====================================================
    st.write("➡️ Generando PRESUPUESTO")

    elems.append(Paragraph("PRESUPUESTO DE ESTRUCTURAS", styles["Heading1"]))
    elems.append(Spacer(1, 10))

    bloque_presupuesto = generar_tabla_precios_estructura(
        df_precios_estructura,
        df_estructuras
    )

    st.write("PRESUPUESTO elementos:", len(bloque_presupuesto))
    st.write("Tipos:", [type(x).__name__ for x in bloque_presupuesto])

    elems.extend(bloque_presupuesto)

    elems.append(PageBreak())

    # =====================================================
    # COTIZACIÓN
    # =====================================================
    st.write("➡️ Generando COTIZACIÓN")

    elems.append(Paragraph("COTIZACIÓN DEL PROYECTO", styles["Heading1"]))
    elems.append(Spacer(1, 10))

    bloque_cotizacion = generar_cotizacion_desde_estructuras(
        doc,
        styles,
        df_precios_estructura
    )

    st.write("COTIZACION elementos:", len(bloque_cotizacion))
    st.write("Tipos:", [type(x).__name__ for x in bloque_cotizacion])

    # 🔥 INSPECCIÓN DETALLADA
    for i, e in enumerate(bloque_cotizacion):
        try:
            if hasattr(e, "getPlainText"):
                txt = e.getPlainText()
                if "MATERIALES" in txt.upper():
                    st.error(f"🔥 DETECTADO TEXTO SOSPECHOSO EN COTIZACION [{i}]: {txt}")
        except:
            pass

    elems.extend(bloque_cotizacion)

    # =====================================================
    # DEBUG FINAL DE ELEMS
    # =====================================================
    st.write("➡️ TOTAL ELEMENTOS PDF:", len(elems))

    conteo = {}
    for e in elems:
        t = type(e).__name__
        conteo[t] = conteo.get(t, 0) + 1

    st.write("Resumen de elementos:", conteo)

    # =====================================================
    # BUILD
    # =====================================================
    st.write("➡️ CONSTRUYENDO PDF")

    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    st.success("✅ PDF COMPLETO GENERADO")

    return pdf_bytes
