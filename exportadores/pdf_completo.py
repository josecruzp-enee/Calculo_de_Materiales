# =====================================================
# IMPORTS
# =====================================================
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, PageBreak, Table
)

from exportadores.precios_estructura_pdf import generar_tabla_precios_estructura
from exportadores.hoja_info import seccion_hoja_info
from exportadores.cotizacion_pdf import generar_seccion_cotizacion_final

from io import BytesIO
from reportlab.lib.pagesizes import letter
from exportadores.pdf_base import styles, fondo_pagina


# =====================================================
# PDF COMPLETO (VERSIÓN CLIENTE)
# =====================================================
def generar_pdf_completo(
    df_materiales,
    df_estructuras,
    df_mat_por_punto,
    df_costos_por_punto,
    df_costos_estructura,
    df_precios_estructura,   # 👈 AHORA VIENE CALCULADO
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

    # =====================================================
    # 3. COTIZACIÓN FINAL
    # =====================================================
    if df_precios_estructura is not None and not df_precios_estructura.empty:

        elems.extend(
            generar_seccion_cotizacion_final(
                doc,
                styles,
                df_precios=df_precios_estructura,
                porcentaje_gestion=0.02,
                porcentaje_imprevistos=0.01,
                porcentaje_isv=0.15,
            )
        )

        elems.append(PageBreak())

    # =====================================================
    # 4. LISTA DE MATERIALES
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

        tabla = Table(data)
        elems.append(tabla)

    # =====================================================
    # BUILD
    # =====================================================
    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
