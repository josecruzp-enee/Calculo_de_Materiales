# =====================================================
# IMPORTS
# =====================================================
from exportadores.pdf_reportes_simples import (
    generar_pdf_estructuras_global,
    generar_pdf_materiales,
    generar_pdf_materiales_por_punto,
)
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak, Table
from exportadores.precios_estructura import generar_tabla_costos_estructura
from io import BytesIO
from reportlab.lib.pagesizes import letter
from exportadores.pdf_base import styles, fondo_pagina
from exportadores.hoja_info import hoja_info_proyecto
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

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)

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
    from exportadores.hoja_info import hoja_info_proyecto

    elems.extend(
        hoja_info_proyecto(
            datos_proyecto=datos_proyecto,
            df_estructuras=df_estructuras,
            df_mat=df_materiales,
            styleN=styles["Normal"],
            styleH=styles["Heading2"],
            _calibres_por_tipo=None
        )
    )

    elems.append(PageBreak())
    elems.append(Spacer(1, 12))

    if datos_proyecto:
        nombre = datos_proyecto.get("nombre", "Proyecto")
        elems.append(Paragraph(f"Proyecto: {nombre}", styles["Normal"]))
        elems.append(Spacer(1, 12))

    elems.append(PageBreak())

    # =====================================================
    # 2. COSTOS DE ESTRUCTURA
    # =====================================================
    if df_costos_estructura is not None and not df_costos_estructura.empty:
        elems.extend(
            generar_tabla_costos_estructura(doc, styles, df_costos_estructura)
        )
        elems.append(PageBreak())

    # =====================================================
    # 3. ESTRUCTURAS
    # =====================================================
    if df_estructuras is not None and not df_estructuras.empty:
        elems.append(Paragraph("<b>LISTA DE ESTRUCTURAS</b>", styles["Heading2"]))
        elems.append(Spacer(1, 10))

        data = [["Estructura", "Cantidad"]]

        df = df_estructuras.groupby("Estructura")["Cantidad"].sum().reset_index()

        for _, r in df.iterrows():
            data.append([str(r["Estructura"]), str(int(r["Cantidad"]))])

        tabla = Table(data)
        elems.append(tabla)
        elems.append(PageBreak())

    # =====================================================
    # 4. MATERIALES
    # =====================================================
    if df_materiales is not None and not df_materiales.empty:
        elems.append(Paragraph("<b>LISTA DE MATERIALES</b>", styles["Heading2"]))
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
        elems.append(PageBreak())

    # =====================================================
    # 5. MATERIALES POR PUNTO
    # =====================================================
    if df_mat_por_punto is not None and not df_mat_por_punto.empty:
        elems.append(Paragraph("<b>MATERIALES POR PUNTO</b>", styles["Heading2"]))
        elems.append(Spacer(1, 10))

        data = [["Punto", "Material", "Cantidad"]]

        for _, r in df_mat_por_punto.head(200).iterrows():
            data.append([
                str(r.get("Punto", "")),
                str(r.get("Materiales", "")),
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
