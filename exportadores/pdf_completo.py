# -*- coding: utf-8 -*-
from __future__ import annotations

from exportadores.cotizacion import generar_seccion_cotizacion_final

from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, PageBreak, Table, TableStyle
)

from reportlab.lib import colors

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
    resultado_costos_proyecto=None
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
        df_mat=df_materiales,
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
    # 4. COSTOS DE PROYECTO (MODELO OBRA)
    # =====================================================
    elems.append(PageBreak())

    elems.append(Paragraph("COSTOS DE PROYECTO", styles["Heading1"]))
    elems.append(Spacer(1, 10))

    if resultado_costos_proyecto is None:

        elems.append(Paragraph(
            "No se dispone del cálculo de costos de proyecto.",
            styles["Normal"]
        ))

    else:

        r = resultado_costos_proyecto

        # -------------------------------------------------
        # 🔹 DATOS DEL PROYECTO (NUEVO)
        # -------------------------------------------------
        elems.append(Paragraph("Datos del Proyecto", styles["Heading2"]))
        elems.append(Spacer(1, 6))

        data_info = [
            ["Concepto", "Valor"],
            ["Total estructuras", r.get("total_estructuras", 0)],
            ["Postes", r.get("num_postes", 0)],
            ["Retenidas", r.get("num_retenidas", 0)],
            ["Agujeros", r.get("total_agujeros", 0)],
            ["Longitud primaria (m)", r.get("longitud_primario", 0)],
            ["Longitud secundaria (m)", r.get("longitud_secundario", 0)],
        ]

        tabla_info = Table(data_info)

        tabla_info.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.black),
            ("BACKGROUND", (0,0), (-1,0), colors.grey),
        ]))

        elems.append(tabla_info)
        elems.append(Spacer(1, 10))

        # -------------------------------------------------
        # 🔹 COSTOS (TU BLOQUE ORIGINAL)
        # -------------------------------------------------
        data = [
            ["Concepto", "Valor"],
            ["Días totales", str(r.get("dias_totales", 0))],
            ["Costo materiales", f"L {r.get('costo_materiales',0):,.2f}"],
            ["Costo cuadrilla", f"L {r.get('costo_cuadrilla',0):,.2f}"],
            ["Costo agujeros", f"L {r.get('costo_agujeros',0):,.2f}"],
            ["Costo grúa", f"L {r.get('costo_grua',0):,.2f}"],
            ["ENEE", f"L {r.get('costo_enee',0):,.2f}"],
            ["Contingencia", f"L {r.get('contingencia',0):,.2f}"],
            ["Costo total real", f"L {r.get('costo_total_real',0):,.2f}"],
            ["Precio venta", f"L {r.get('precio_venta',0):,.2f}"],
            ["Utilidad", f"L {r.get('utilidad',0):,.2f}"],
            ["Margen (%)", f"{r.get('margen_pct',0)} %"],
        ]

        tabla = Table(data, repeatRows=1)

        tabla.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.black),
            ("BACKGROUND", (0,0), (-1,0), colors.grey),
        ]))

        elems.append(tabla)

    # =====================================================
    # BUILD
    # =====================================================
    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    _log("✅ PDF GENERADO")

    return pdf_bytes
