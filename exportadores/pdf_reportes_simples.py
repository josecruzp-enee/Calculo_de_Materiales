# -*- coding: utf-8 -*-
"""
exportadores/pdf_reportes_simples.py
Reportes PDF unitarios: materiales/estructuras global y por punto.
Autor: José Nikol Cruz
"""

import pandas as pd
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER

from exportadores.pdf_base import (
    styles,
    styleN,
    fondo_pagina,
    formatear_material,
    estilo_tabla,
    nombre_proyecto_seguro,
)

def _debug_indice(base_datos):
    import streamlit as st
    import pandas as pd

    st.write("DEBUG ▶ base_datos keys:", list(base_datos.keys()) if base_datos else "None")
    st.write("DEBUG ▶ primeras keys reales:", list(base_datos.keys())[:20])  # 🔥 ESTA LÍNEA NUEVA

    df_indice = None
    if base_datos:
        df_indice = base_datos.get("indice") or base_datos.get("INDICE")

    st.write("DEBUG ▶ df_indice tipo:", type(df_indice))

    if isinstance(df_indice, pd.DataFrame):
        st.write("DEBUG ▶ columnas indice:", list(df_indice.columns))
        st.write("DEBUG ▶ muestra indice:", df_indice.head(3))

        df_idx = df_indice.copy()
        df_idx.columns = [str(c).strip().lower() for c in df_idx.columns]

        st.write("DEBUG ▶ columnas normalizadas:", df_idx.columns.tolist())

        col_codigo = next((c for c in df_idx.columns if "codigo" in c), None)
        col_desc   = next((c for c in df_idx.columns if "descrip" in c), None)

        st.write("DEBUG ▶ col_codigo:", col_codigo)
        st.write("DEBUG ▶ col_desc:", col_desc)

        if col_codigo and col_desc:
            mapa_desc = dict(zip(
                df_idx[col_codigo].astype(str).str.strip().str.upper(),
                df_idx[col_desc].astype(str).str.strip()
            ))

            st.write("DEBUG ▶ mapa_len:", len(mapa_desc))
            st.write("DEBUG ▶ sample mapa:", list(mapa_desc.items())[:5])

# ==========================================================
# 🎯 HEADER ESTÁNDAR (NUEVO)
# ==========================================================
def _header(titulo, nombre_proy):

    from reportlab.lib.enums import TA_CENTER

    styleTitulo = styles["Title"].clone("titulo_center")
    styleTitulo.alignment = TA_CENTER

    styleProyecto = styles["Normal"].clone("proyecto_center")
    styleProyecto.alignment = TA_CENTER
    styleProyecto.fontSize = 11      # 🔥 AJUSTE CLAVE
    styleProyecto.leading = 13

    return [
        Paragraph(titulo, styleTitulo),
        Spacer(1, 6),
        Paragraph(f"<b>Proyecto:</b> {escape(str(nombre_proy))}", styleProyecto),
        Spacer(1, 12),
    ]


# ==========================================================
# PDF: RESUMEN DE MATERIALES (GLOBAL)
# ==========================================================
def generar_pdf_materiales(df_mat, nombre_proy, datos_proyecto=None):

    nombre_proy = nombre_proyecto_seguro(nombre_proy, datos_proyecto)

    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = _header("RESUMEN DE MATERIALES", nombre_proy)

    if df_mat is None or df_mat.empty:
        elems.append(Paragraph("No se encontraron materiales.", styleN))
        doc.build(elems)
        return buffer.getvalue()

    df_agrupado = df_mat.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

    data = [["Material", "Unidad", "Cantidad"]]

    for _, row in df_agrupado.iterrows():
        data.append([
            Paragraph(formatear_material(row["Materiales"]), styleN),
            escape(str(row["Unidad"])),
            f"{float(row['Cantidad']):.2f}"
        ])

    tabla = Table(data, colWidths=[4 * inch, 1 * inch, 1 * inch], repeatRows=1)
    tabla.setStyle(estilo_tabla())

    elems.append(tabla)
    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ==========================================================
# PDF: RESUMEN DE ESTRUCTURAS (GLOBAL)
# ==========================================================
def generar_pdf_estructuras_global(df_estructuras, nombre_proy, base_datos=None, datos_proyecto=None):

    nombre_proy = nombre_proyecto_seguro(nombre_proy, datos_proyecto)

    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    def _safe(texto):
        return escape("" if pd.isna(texto) else str(texto))

    elems = _header("RESUMEN DE ESTRUCTURAS", nombre_proy)

    if df_estructuras is None or df_estructuras.empty:
        elems.append(Paragraph("No se encontraron estructuras.", styleN))
        doc.build(elems)
        return buffer.getvalue()

    df = df_estructuras.copy()

    col_codigo = "codigodeestructura" if "codigodeestructura" in df.columns else "Estructura"

    df[col_codigo] = (
        df[col_codigo]
        .astype(str)
        .str.replace("■", "")
        .str.strip()
        .str.upper()
    )

    _debug_indice(base_datos)

    
    if base_datos and "indice" in base_datos:

        df_indice = base_datos["indice"]

        if isinstance(df_indice, pd.DataFrame):

            df_indice["Código de Estructura"] = (
                df_indice["Código de Estructura"]
                .astype(str)
                .str.strip()
                .str.upper()
            )

            mapa_desc = dict(zip(
                df_indice["Código de Estructura"],
                df_indice["Descripción"]
            ))

            df["Descripcion"] = df[col_codigo].map(mapa_desc).fillna("")

    else:
        df["Descripcion"] = df.get("Descripcion", "").fillna("").astype(str)

    if "Cantidad" not in df.columns:
        df["Cantidad"] = 1

    df = df.groupby(col_codigo, as_index=False).agg({
        "Cantidad": "sum",
        "Descripcion": "first"
    })

    data = [["Estructura", "Descripción", "Cantidad"]]

    for _, r in df.iterrows():
        data.append([
            Paragraph(_safe(r[col_codigo]), styleN),
            Paragraph(_safe(r["Descripcion"]), styleN),
            Paragraph(str(int(r["Cantidad"])), styleN),
        ])

    tabla = Table(data, colWidths=[2 * inch, 3.5 * inch, 1 * inch], repeatRows=1)
    tabla.setStyle(estilo_tabla())

    elems.append(tabla)
    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ==========================================================
# PDF: ESTRUCTURAS POR PUNTO
# ==========================================================
def generar_pdf_estructuras_por_punto(df, nombre_proy, datos_proyecto=None):

    nombre_proy = nombre_proyecto_seguro(nombre_proy, datos_proyecto)

    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = _header("ESTRUCTURAS POR PUNTO", nombre_proy)

    if df is None or df.empty:
        elems.append(Paragraph("No hay datos.", styleN))
        doc.build(elems)
        return buffer.getvalue()

    col_codigo = "codigodeestructura" if "codigodeestructura" in df.columns else "Estructura"

    for punto, df_p in df.groupby("Punto"):

        elems.append(Paragraph(f"<b>{punto}</b>", styles["Heading2"]))

        data = [["Estructura", "Descripción", "Cantidad"]]

        for _, r in df_p.iterrows():
            data.append([
                escape(str(r.get(col_codigo, ""))),
                escape(str(r.get("Descripcion", ""))),
                escape(str(r.get("Cantidad", ""))),
            ])

        tabla = Table(
            data,
            colWidths=[
                doc.width * 0.18,
                doc.width * 0.67,
                doc.width * 0.15
            ],
            repeatRows=1
        )

        tabla.setStyle(estilo_tabla())

        elems.append(tabla)
        elems.append(Spacer(1, 10))

    doc.build(elems)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ==========================================================
# PDF: MATERIALES POR PUNTO
# ==========================================================
def generar_pdf_materiales_por_punto(df, nombre_proy, datos_proyecto=None):

    nombre_proy = nombre_proyecto_seguro(nombre_proy, datos_proyecto)

    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = _header("MATERIALES POR PUNTO", nombre_proy)

    if df is None or df.empty:
        elems.append(Paragraph("No hay materiales.", styleN))
        doc.build(elems)
        return buffer.getvalue()

    for punto, df_p in df.groupby("Punto"):

        elems.append(Paragraph(f"<b>{punto}</b>", styles["Heading2"]))

        df_agr = df_p.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

        data = [["Material", "Unidad", "Cantidad"]]

        for _, r in df_agr.iterrows():
            data.append([
                Paragraph(formatear_material(r["Materiales"]), styleN),
                escape(str(r["Unidad"])),
                f"{float(r['Cantidad']):.2f}",
            ])

        tabla = Table(
            data,
            colWidths=[
                doc.width * 0.55,
                doc.width * 0.20,
                doc.width * 0.25
            ],
            repeatRows=1
        )

        tabla.setStyle(estilo_tabla())

        elems.append(tabla)
        elems.append(Spacer(1, 10))

    doc.build(elems)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
