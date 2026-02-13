# -*- coding: utf-8 -*-
"""
exportadores/pdf_completo.py
PDF completo principal (orquestador).
Autor: José Nikol Cruz
"""

import re
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors

from exportadores.cables_pdf import tabla_cables_pdf
from exportadores.hoja_info import hoja_info_proyecto

from exportadores.pdf_base import (
    styles, styleN, styleH,
    fondo_pagina,
    salto_pagina_seguro, extender_flowables, quitar_saltos_finales,
    formatear_material,
    _calibres_por_tipo,
)

from exportadores.pdf_reportes_simples import _tabla_estructuras_por_punto
from exportadores.pdf_anexos_costos import (tabla_costos_materiales_pdf, tabla_mano_obra_estructuras_pdf,)



def generar_pdf_completo(
    df_mat,
    df_estructuras,
    df_estructuras_por_punto,
    df_mat_por_punto,
    datos_proyecto,
    df_costos=None,
    df_costos_estructuras=None
):
    """
    Genera el PDF total del proyecto incluyendo:
    - Hoja de Información del Proyecto
    - Resumen de Materiales (global) (SIN precios)
    - Tabla de Cables
    - Resumen de Estructuras (global)
    - Estructuras por Punto
    - Materiales por Punto
    - ANEXO: Costos de Materiales (si df_costos viene)
    """
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = []

    # ---------------------------
    # Hoja de información
    # ---------------------------
    elems = extender_flowables(
        elems,
        hoja_info_proyecto(
            datos_proyecto,
            df_estructuras,
            df_mat,
            styles=styles,
            styleN=styleN,
            styleH=styleH,
            _calibres_por_tipo=_calibres_por_tipo
        )
    )

    # ---------------------------
    # Resumen de materiales (GLOBAL)
    # ---------------------------
    salto_pagina_seguro(elems)
    elems.append(Paragraph("<b>Resumen de Materiales</b>", styles["Heading2"]))

    if df_mat is not None and not df_mat.empty:
        dfm = df_mat.copy()
        dfm.columns = [str(c).strip() for c in dfm.columns]

        df_agr = dfm.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
        data = [["Material", "Unidad", "Cantidad"]]

        for _, r in df_agr.iterrows():
            data.append([
                Paragraph(formatear_material(r["Materiales"]), styleN),
                escape(str(r["Unidad"])),
                f"{float(r['Cantidad']):.2f}",
            ])

        tabla = Table(data, colWidths=[4 * inch, 1 * inch, 1 * inch])
        tabla.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elems.append(tabla)
    else:
        elems.append(Paragraph("No se encontraron materiales.", styleN))

    # ---------------------------
    # Tabla de cables
    # ---------------------------
    elems = extender_flowables(elems, tabla_cables_pdf(datos_proyecto))

    # ---------------------------
    # Resumen de estructuras (GLOBAL)
    # ---------------------------
    salto_pagina_seguro(elems)
    elems.append(Paragraph("<b>Resumen de Estructuras</b>", styles["Heading2"]))

    if df_estructuras is not None and not df_estructuras.empty:
        dfe = df_estructuras.copy()
        dfe.columns = [str(c).strip() for c in dfe.columns]
        elems.append(_tabla_estructuras_por_punto("GLOBAL", dfe, doc.width))
    else:
        elems.append(Paragraph("No se encontraron estructuras.", styleN))

    # ---------------------------
    # Estructuras por punto
    # ---------------------------
    if df_estructuras_por_punto is not None and not df_estructuras_por_punto.empty:
        salto_pagina_seguro(elems)
        elems.append(Paragraph("<b>Estructuras por Punto</b>", styles["Heading2"]))

        dfep = df_estructuras_por_punto.copy()
        dfep.columns = [str(c).strip() for c in dfep.columns]

        puntos = sorted(
            dfep["Punto"].unique(),
            key=lambda x: int(re.sub(r"\D", "", str(x)) or 0)
        )

        for p in puntos:
            m = re.search(r"(\d+)", str(p))
            num = m.group(1) if m else str(p)

            elems.append(Paragraph(f"<b>Punto {escape(num)}</b>", styles["Heading3"]))
            df_p = dfep[dfep["Punto"] == p]
            elems.append(_tabla_estructuras_por_punto(num, df_p, doc.width))
            elems.append(Spacer(1, 0.2 * inch))

    # ---------------------------
    # Materiales por punto
    # ---------------------------
    if df_mat_por_punto is not None and not df_mat_por_punto.empty:
        salto_pagina_seguro(elems)
        elems.append(Paragraph("<b>Materiales por Punto</b>", styles["Heading2"]))

        dfmp = df_mat_por_punto.copy()
        dfmp.columns = [str(c).strip() for c in dfmp.columns]

        required = {"Punto", "Materiales", "Unidad", "Cantidad"}
        if not required.issubset(set(dfmp.columns)):
            faltan = ", ".join(sorted(required - set(dfmp.columns)))
            elems.append(Paragraph(
                f"⚠️ No se puede mostrar 'Materiales por Punto'. Faltan columnas: {escape(faltan)}",
                styleN
            ))
        else:
            puntos = sorted(
                dfmp["Punto"].unique(),
                key=lambda x: int(re.sub(r"\D", "", str(x)) or 0)
            )

            for p in puntos:
                m = re.search(r"(\d+)", str(p))
                num = m.group(1) if m else str(p)

                elems.append(Paragraph(f"<b>Punto {escape(num)}</b>", styles["Heading3"]))
                df_p = dfmp[dfmp["Punto"] == p]

                df_agr = df_p.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

                data = [["Material", "Unidad", "Cantidad"]]
                for _, r in df_agr.iterrows():
                    data.append([
                        Paragraph(formatear_material(r["Materiales"]), styleN),
                        escape(str(r["Unidad"])),
                        f"{float(r['Cantidad']):.2f}",
                    ])

                tabla = Table(data, colWidths=[4 * inch, 1 * inch, 1 * inch])
                tabla.setStyle(TableStyle([
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.darkgreen),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]))
                elems.append(tabla)
                elems.append(Spacer(1, 0.2 * inch))

    # ---------------------------
    # ANEXO A: Costos de Materiales (al final del PDF completo)
    # ---------------------------
    if df_costos is not None and hasattr(df_costos, "empty") and not df_costos.empty:
        salto_pagina_seguro(elems)
        elems = extender_flowables(elems, tabla_costos_materiales_pdf(df_costos))

    # (B y C siguen comentados en tu original; los dejamos igual)

    

    # ---------------------------
    # ANEXO B: Mano de Obra por Estructura (NO depende de materiales)
    # ---------------------------
    if df_costos_estructuras is not None and hasattr(df_costos_estructuras, "empty") and not df_costos_estructuras.empty:
        salto_pagina_seguro(elems)
        elems = extender_flowables(
            elems,
            tabla_mano_obra_estructuras_pdf(
                df_costos_estructuras,
                styles=styles,
                styleN=styleN,
                doc_width=doc.width
            )
        )
    quitar_saltos_finales(elems)
    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()
        
    return pdf_bytes
