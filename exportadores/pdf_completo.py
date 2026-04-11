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
# PDF COMPLETO (LIMPIO)
# =====================================================
def generar_pdf_completo(
    df_materiales,
    df_estructuras,
    df_precios_estructura,
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
    # HOJA INFO
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
    # NORMALIZAR PRECIOS
    # =====================================================
    if df_precios_estructura is None:
        import pandas as pd
        df_precios_estructura = pd.DataFrame(columns=[
            "Estructura", "Cantidad", "Precio Unitario", "Subtotal"
        ])

    else:
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

        if "Precio Unitario" not in df_precios_estructura.columns:
            df_precios_estructura["Precio Unitario"] = 0

        if "Subtotal" not in df_precios_estructura.columns:
            df_precios_estructura["Subtotal"] = (
                df_precios_estructura["Precio Unitario"] *
                df_precios_estructura["Cantidad"]
            )

    # =====================================================
    # PRESUPUESTO
    # =====================================================
    elems.append(Paragraph("PRESUPUESTO DE ESTRUCTURAS", styles["Heading1"]))
    elems.append(Spacer(1, 10))

    elems.extend(
        generar_tabla_precios_estructura(
            df_precios_estructura,
            df_estructuras
        )
    )

    elems.append(PageBreak())

    # =====================================================
    # COTIZACIÓN
    # =====================================================
    elems.append(Paragraph("COTIZACIÓN DEL PROYECTO", styles["Heading1"]))
    elems.append(Spacer(1, 10))

    elems.extend(
        generar_cotizacion_desde_estructuras(
            doc,
            styles,
            df_precios_estructura
        )
    )

    # =====================================================
    # BUILD
    # =====================================================
    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
