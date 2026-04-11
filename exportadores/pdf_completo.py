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


# =====================================================
# PDF COMPLETO (FINAL)
# =====================================================
def generar_pdf_completo(
    df_materiales,
    df_estructuras,
    df_precios_estructura,
    datos_proyecto,
):

    # =====================================================
    # INIT PDF
    # =====================================================
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
    # 1. HOJA INFO
    # =====================================================
    elems.extend(
        seccion_hoja_info(
            datos_proyecto=datos_proyecto,
            df_estructuras=df_estructuras,
            df_mat=df_materiales
        )
    )

    elems.append(PageBreak())

    # =====================================================
    # 🔥 FIX CRÍTICO: ASEGURAR DATA
    # =====================================================
    if df_precios_estructura is None:
        df_precios_estructura = None

    else:
        # asegurar columnas mínimas
        if "Cantidad" not in df_precios_estructura.columns:
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

        if "Subtotal" not in df_precios_estructura.columns:
            df_precios_estructura["Subtotal"] = (
                df_precios_estructura.get("Precio Unitario", 0) *
                df_precios_estructura.get("Cantidad", 0)
            )

    # =====================================================
    # 2. PRESUPUESTO DE ESTRUCTURAS (SIN BLOQUEO)
    # =====================================================
    elems.append(Paragraph("PRESUPUESTO DE ESTRUCTURAS", styles["Heading1"]))
    elems.append(Spacer(1, 10))

    if df_precios_estructura is not None:
        elems.extend(
            generar_tabla_precios_estructura(
                df_precios_estructura,
                df_estructuras
            )
        )
    else:
        elems.append(Paragraph("SIN PRESUPUESTO DISPONIBLE", styles["Normal"]))

    elems.append(PageBreak())

    # =====================================================
    # 3. COTIZACIÓN FINAL (🔥 FORZADA)
    # =====================================================
    elems.append(Paragraph("COTIZACIÓN DEL PROYECTO", styles["Heading1"]))
    elems.append(Spacer(1, 10))

    if df_precios_estructura is not None:
        elems.extend(
            generar_cotizacion_desde_estructuras(
                doc,
                styles,
                df_precios_estructura
            )
        )
    else:
        elems.append(Paragraph("SIN COTIZACIÓN DISPONIBLE", styles["Normal"]))

    # =====================================================
    # BUILD
    # =====================================================
    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
