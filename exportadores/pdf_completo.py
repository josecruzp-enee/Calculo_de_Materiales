# -*- coding: utf-8 -*-
"""
exportadores/pdf_completo.py
PDF PROFESIONAL FINAL (CORREGIDO Y CONSISTENTE)
"""

import re
from io import BytesIO

from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors

from exportadores.cables_pdf import tabla_cables_pdf
from exportadores.hoja_info import hoja_info_proyecto

from exportadores.pdf_base import (
    styles, styleN, styleH,
    fondo_pagina,
    extender_flowables, quitar_saltos_finales,
    formatear_material,
    _calibres_por_tipo,
)

from exportadores.pdf_reportes_simples import _tabla_estructuras_por_punto
from exportadores.pdf_anexos_costos import (
    tabla_costos_materiales_pdf,
    tabla_mano_obra_estructuras_pdf,
)

from exportadores.precios_estructura import (
    generar_tabla_presupuesto,
    procesar_precios_estructura
)

# ==========================================================
# ✅ VALIDACIÓN CENTRAL
# ==========================================================

def _validar_columnas(df, requeridas, nombre):
    if df is None:
        raise ValueError(f"{nombre} es None")

    faltantes = [c for c in requeridas if c not in df.columns]
    if faltantes:
        raise ValueError(f"{nombre} no tiene columnas: {faltantes}")

def _seccion_costos_materiales(df_costos):
    elems = [PageBreak()]

    elems.append(Paragraph("<b>4. COSTOS DE MATERIALES</b>", styles["Heading2"]))
    elems.append(Spacer(1, 0.3 * inch))

    if df_costos is None or df_costos.empty:
        elems.append(Paragraph("No hay costos de materiales.", styleN))
        return elems

    elems += tabla_costos_materiales_pdf(df_costos)

    return elems
    
# ==========================================================
# 🔥 UTILIDAD COSTOS
# ==========================================================

def _sumar_costos(df):
    if df is None or df.empty:
        return 0.0

    for col in df.columns:
        nombre = str(col).lower().strip()

        if "costo" in nombre or "total" in nombre:
            df_clean = df.copy()

            for c in df_clean.columns:
                if "material" in str(c).lower():
                    df_clean = df_clean[
                        ~df_clean[c].astype(str).str.upper().str.contains(
                            "SUBTOTAL|ISV|TOTAL", na=False
                        )
                    ]

            return float(df_clean[col].fillna(0).sum())

    return 0.0


# ==========================================================
# 🚀 ORQUESTADOR PDF
# ==========================================================

def generar_pdf_completo(
    df_mat,
    df_estructuras,
    df_estructuras_por_punto,
    df_mat_por_punto,
    datos_proyecto,
    df_costos=None,
    df_mo_estructuras=None,
):
    buffer, doc, elems = _crear_documento(datos_proyecto)

    elems += _seccion_info(datos_proyecto, df_estructuras, df_mat)

    df_precios = procesar_precios_estructura()
    elems += generar_tabla_presupuesto(doc, styles, df_estructuras, df_precios)

    elems += _seccion_estructuras_global(doc, df_estructuras)
    elems += _seccion_materiales_global(doc, df_mat)
    elems += _seccion_costos_materiales(df_costos)
    elems += _seccion_mano_obra(df_mo_estructuras)
    elems += _seccion_cotizacion(doc, df_costos, df_mo_estructuras)
    elems += _seccion_estructuras_por_punto(doc, df_estructuras_por_punto)
    elems += _seccion_materiales_por_punto(doc, df_mat_por_punto)

    quitar_saltos_finales(elems)
    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes


# ==========================================================
# 📄 BASE DOCUMENTO
# ==========================================================

def _crear_documento(datos_proyecto):
    buffer = BytesIO()

    doc = BaseDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=60,
        rightMargin=60,
        topMargin=160,
        bottomMargin=50
    )

    doc.membrete_pdf = datos_proyecto.get("membrete_pdf", "SMART")

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)

    template = PageTemplate(
        id="fondo",
        frames=[frame],
        onPage=fondo_pagina
    )

    doc.addPageTemplates([template])

    return buffer, doc, []


# ==========================================================
# 🎨 ESTILO TABLA
# ==========================================================

def _tabla_estilo_pro():
    return TableStyle([
        ("LINEBELOW", (0,0), (-1,0), 1.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#EAEAEA")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ])


# ==========================================================
# 📊 SECCIONES
# ==========================================================

def _seccion_info(datos_proyecto, df_estructuras, df_mat):
    return extender_flowables(
        [],
        hoja_info_proyecto(
            datos_proyecto,
            df_estructuras,
            df_mat,
            styleN=styleN,
            styleH=styleH,
            _calibres_por_tipo=_calibres_por_tipo
        )
    )


def _seccion_estructuras_global(doc, df):
    elems = [PageBreak()]

    elems.append(Paragraph("<b>2. LISTA DE ESTRUCTURAS</b>", styles["Heading2"]))
    elems.append(Spacer(1, 0.3 * inch))

    if df is None or df.empty:
        elems.append(Paragraph("No hay estructuras.", styleN))
        return elems

    import pandas as pd

    # Detectar columnas dinámicamente
    col_est = next((c for c in df.columns if "estruct" in c.lower()), None)
    col_cant = next((c for c in df.columns if "cant" in c.lower()), None)

    if col_est is None:
        raise ValueError("No se encontró columna de estructuras")

    df_fix = pd.DataFrame({
        "Estructura": df[col_est],
        "Descripción": df[col_est],
        "Cantidad": df[col_cant] if col_cant else 1
    })

    elems.append(_tabla_estructuras_por_punto("GLOBAL", df_fix, doc.width))
    return elems


def _seccion_materiales_global(doc, df_mat):
    elems = [PageBreak()]

    elems.append(Paragraph("<b>3. LISTA DE MATERIALES</b>", styles["Heading2"]))
    elems.append(Spacer(1, 0.3 * inch))

    _validar_columnas(df_mat, ["Materiales", "Unidad", "Cantidad"], "materiales_global")

    df_agr = df_mat.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

    data = [["Material", "Unidad", "Cantidad"]]

    for _, r in df_agr.iterrows():
        data.append([
            Paragraph(formatear_material(r["Materiales"]), styleN),
            r["Unidad"],
            f"{float(r['Cantidad']):,.2f}",
        ])

    tabla = Table(data, colWidths=[doc.width * 0.65, doc.width * 0.15, doc.width * 0.20])
    tabla.setStyle(_tabla_estilo_pro())

    elems.append(tabla)
    return elems


def _seccion_estructuras_por_punto(doc, df):
    _validar_columnas(df, ["Punto"], "estructuras_por_punto")

    elems = [PageBreak()]
    elems.append(Paragraph("<b>7. DETALLE POR PUNTO</b>", styles["Heading2"]))
    elems.append(Spacer(1, 0.3 * inch))

    puntos = sorted(df["Punto"].unique())

    for p in puntos:
        match = re.search(r"\d+", str(p))
        num = match.group() if match else str(p)

        elems.append(Paragraph(f"<b>Punto {num}</b>", styles["Heading3"]))

        df_p = df[df["Punto"] == p]
        elems.append(_tabla_estructuras_por_punto(num, df_p, doc.width))
        elems.append(Spacer(1, 0.2 * inch))

    return elems


def _seccion_materiales_por_punto(doc, df):
    _validar_columnas(df, ["Punto", "Materiales", "Unidad", "Cantidad"], "materiales_por_punto")

    elems = [PageBreak()]
    elems.append(Paragraph("<b>8. MATERIALES POR PUNTO</b>", styles["Heading2"]))
    elems.append(Spacer(1, 0.3 * inch))

    for p in sorted(df["Punto"].unique()):
        match = re.search(r"\d+", str(p))
        num = match.group() if match else str(p)

        elems.append(Paragraph(f"<b>Punto {num}</b>", styles["Heading3"]))

        df_p = df[df["Punto"] == p]
        df_agr = df_p.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

        data = [["Material", "Unidad", "Cantidad"]]

        for _, r in df_agr.iterrows():
            data.append([
                Paragraph(formatear_material(r["Materiales"]), styleN),
                r["Unidad"],
                f"{float(r['Cantidad']):,.2f}",
            ])

        tabla = Table(data, colWidths=[doc.width * 0.65, doc.width * 0.15, doc.width * 0.20])
        tabla.setStyle(_tabla_estilo_pro())

        elems.append(tabla)
        elems.append(Spacer(1, 0.3 * inch))

    return elems
