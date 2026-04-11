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

from costos_precios.precio_por_estructura import calcular_precios_por_estructura

from io import BytesIO
from reportlab.lib.pagesizes import letter
from exportadores.pdf_base import styles, fondo_pagina


# =====================================================
# PDF COMPLETO (AUTÓNOMO)
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
    elems.extend(
        seccion_hoja_info(
            datos_proyecto=datos_proyecto,
            df_estructuras=df_estructuras,
            df_mat=df_materiales
        )
    )

    elems.append(PageBreak())

    # =====================================================
    # 2. CALCULAR PRECIOS (INTERNO 🔥)
    # =====================================================
    df_precios_estructura = None

    if df_costos_estructura is not None and not df_costos_estructura.empty:
        try:
            df_precios_estructura, _ = calcular_precios_por_estructura(
                df_costos_estructura,
                df_estructuras,
                porcentaje_utilidad=0.15,
                costo_cuadrilla_dia=10000,
                fraccion_jornada=1/16,
            )
        except Exception as e:
            elems.append(Paragraph(f"ERROR PRECIOS: {str(e)}", styles["Normal"]))

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

    else:
        elems.append(Paragraph("SIN PRESUPUESTO DE ESTRUCTURAS", styles["Normal"]))
        elems.append(PageBreak())

    # =====================================================
    # 4. COTIZACIÓN FINAL
    # =====================================================
    if df_precios_estructura is not None and not df_precios_estructura.empty:

        try:
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
        except Exception as e:
            elems.append(Paragraph(f"ERROR COTIZACIÓN: {str(e)}", styles["Normal"]))

    else:
        elems.append(Paragraph("SIN COTIZACIÓN DISPONIBLE", styles["Normal"]))

    # =====================================================
    # BUILD
    # =====================================================
    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
