# =====================================================
# IMPORTS
# =====================================================
from exportadores.pdf_reportes_simples import (
    generar_pdf_estructuras_global,
    generar_pdf_materiales,
    generar_pdf_materiales_por_punto,
)

from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, PageBreak, Table
)

# 🔥 EXPORTADOR (PDF)
from exportadores.precios_estructura_pdf import generar_tabla_precios_estructura

from exportadores.hoja_info import seccion_hoja_info

# 🔥 DOMINIO (CÁLCULO)
from costos_precios.precios_por_estructura import calcular_precios_por_estructura

from io import BytesIO
from reportlab.lib.pagesizes import letter
from exportadores.pdf_base import styles, fondo_pagina


# =====================================================
# PDF COMPLETO
# =====================================================
def generar_pdf_completo(
    df_materiales,
    df_estructuras,
    df_mat_por_punto,
    df_costos_por_punto,
    df_costos_estructura,
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
    # 1. PORTADA
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
    # 2. PRECIOS (CORE)
    # =====================================================
    df_precios_estructura = None

    if df_costos_estructura is not None and not df_costos_estructura.empty:

        df_precios_estructura = calcular_precios_por_estructura(
            df_costos_estructura,
            porcentaje_utilidad=0.15,
            costo_cuadrilla_dia=10000,
            fraccion_jornada=1/16,
        )

    # =====================================================
    # 3. PRESUPUESTO
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

    # =====================================================
    # 4. ESTRUCTURAS
    # =====================================================
    if df_estructuras is not None and not df_estructuras.empty:

        elems.append(Paragraph("LISTA DE ESTRUCTURAS", styles["Heading2"]))
        elems.append(Spacer(1, 10))

        data = [["Estructura", "Cantidad"]]

        df = df_estructuras.groupby("Estructura")["Cantidad"].sum().reset_index()

        for _, r in df.iterrows():
            data.append([
                str(r["Estructura"]),
                str(int(r["Cantidad"]))
            ])

        elems.append(Table(data))
        elems.append(PageBreak())

    # =====================================================
    # 5. MATERIALES
    # =====================================================
    if df_materiales is not None and not df_materiales.empty:

        elems.append(Paragraph("LISTA DE MATERIALES", styles["Heading2"]))
        elems.append(Spacer(1, 10))

        data = [["Material", "Unidad", "Cantidad"]]

        for _, r in df_materiales.iterrows():
            data.append([
                str(r.get("Materiales", "")),
                str(r.get("Unidad", "")),
                str(r.get("Cantidad", "")),
            ])

        elems.append(Table(data))
        elems.append(PageBreak())

    # =====================================================
    # 6. MATERIALES POR PUNTO
    # =====================================================
    if df_mat_por_punto is not None and not df_mat_por_punto.empty:

        elems.append(Paragraph("MATERIALES POR PUNTO", styles["Heading2"]))
        elems.append(Spacer(1, 10))

        data = [["Punto", "Material", "Cantidad"]]

        for _, r in df_mat_por_punto.head(200).iterrows():
            data.append([
                str(r.get("Punto", "")),
                str(r.get("Materiales", "")),
                str(r.get("Cantidad", "")),
            ])

        elems.append(Table(data))

    # =====================================================
    # BUILD
    # =====================================================
    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
