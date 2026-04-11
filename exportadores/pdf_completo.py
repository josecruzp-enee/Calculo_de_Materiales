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
    generar_cotizacion_desde_estructuras   # 🔥 ESTA ES LA BUENA
)

from io import BytesIO
from reportlab.lib.pagesizes import letter
from exportadores.pdf_base import styles, fondo_pagina


# =====================================================
# PDF COMPLETO FINAL (FUNCIONANDO)
# =====================================================
def generar_pdf_completo(
    df_materiales,
    df_estructuras,
    df_mat_por_punto,
    df_costos_por_punto,
    df_costos_estructura,
    df_precios_estructura,   # 🔥 IMPORTANTE
    datos_proyecto,
):

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
    # 2. PRESUPUESTO DE ESTRUCTURAS
    # =====================================================
    if df_precios_estructura is not None and not df_precios_estructura.empty:

        elems.append(Paragraph("PRESUPUESTO DE ESTRUCTURAS", styles["Heading1"]))
        elems.append(Spacer(1, 10))

        elems.extend(
            generar_tabla_precios_estructura(
                df_precios_estructura,
                df_estructuras
            )
        )

        elems.append(PageBreak())

    else:
        elems.append(Paragraph("SIN PRESUPUESTO DISPONIBLE", styles["Normal"]))
        elems.append(PageBreak())

    # =====================================================
    # 3. COTIZACIÓN FINAL (🔥 ESTA ES LA CORRECTA)
    # =====================================================
    if df_precios_estructura is not None and not df_precios_estructura.empty:

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
