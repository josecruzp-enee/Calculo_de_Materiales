# -*- coding: utf-8 -*-
"""
exportadores/pdf_utils.py
Generación de informes PDF del cálculo de materiales y estructuras
Autor: José Nikol Cruz
"""

from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
    Table, TableStyle, PageBreak
)
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from datetime import datetime
from io import BytesIO
import os
import re
import pandas as pd
from xml.sax.saxutils import escape

# --- Importación de tabla de cables y hoja de info ---
from exportadores.cables_pdf import tabla_cables_pdf
from exportadores.hoja_info import hoja_info_proyecto


# ======== ESTILOS COMUNES ========
styles = getSampleStyleSheet()
styleN = ParagraphStyle(
    name="Normal9",
    parent=styles["Normal"],
    fontSize=9,
    leading=11
)
styleH = styles["Heading1"]

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# ==========================================================
# FIX: formatear_material (IDENTIDAD)
# ==========================================================
def formatear_material(nombre):
    """Convierte a texto seguro para Paragraph."""
    if nombre is None or (isinstance(nombre, float) and pd.isna(nombre)):
        return ""
    return escape(str(nombre).strip())


# ==========================
# HELPERS (ANTI PÁGINAS EN BLANCO)
# ==========================
def salto_pagina_seguro(elems):
    if elems and not isinstance(elems[-1], PageBreak):
        elems.append(PageBreak())


def extender_flowables(elems, extra):
    if not extra:
        return elems
    if elems and isinstance(elems[-1], PageBreak) and isinstance(extra[0], PageBreak):
        extra = extra[1:]
    elems.extend(extra)
    return elems


def quitar_saltos_finales(elems):
    while elems and isinstance(elems[-1], PageBreak):
        elems.pop()
    return elems


# ==========================
# FONDO DE PÁGINA
# ==========================
def fondo_pagina(canvas, doc):
    try:
        canvas.saveState()
        fondo = os.path.join(BASE_DIR, "data", "data/Smart.jpg")
        ancho, alto = letter
        if os.path.exists(fondo):
            canvas.drawImage(
                fondo, 0, 0,
                width=ancho,
                height=alto,
                mask="auto"
            )
        canvas.restoreState()
    except Exception as e:
        print(f"⚠️ Error aplicando fondo: {e}")


# ==========================================================
# CALIBRES desde tabla de Cables (sin longitudes)
# ==========================================================
def _dedupe_keep_order(vals):
    seen = set()
    out = []
    for v in vals:
        k = str(v).strip().upper()
        if not k:
            continue
        if k in seen:
            continue
        seen.add(k)
        out.append(str(v).strip())
    return out


def _calibres_por_tipo(cables, tipo_buscar: str) -> str:
    """
    Devuelve calibres únicos separados por coma para un tipo de cable:
    MT, BT, N, HP, RETENIDA.
    Lee claves flexibles: "Tipo"/"tipo" y "Calibre"/"calibre".
    """
    t = (tipo_buscar or "").strip().upper()
    if not cables:
        return ""
    calibres = []
    for c in cables:
        tipo = str(c.get("Tipo", c.get("tipo", ""))).strip().upper()
        if tipo != t:
            continue
        cal = str(c.get("Calibre", c.get("calibre", ""))).strip()
        if cal:
            calibres.append(cal)
    calibres = _dedupe_keep_order(calibres)
    return ", ".join(calibres)


# ==========================================================
# PDF: RESUMEN DE MATERIALES (GLOBAL)
# ==========================================================
def generar_pdf_materiales(df_mat, nombre_proy, datos_proyecto=None):
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = [
        Paragraph(f"<b>Resumen de Materiales - Proyecto: {escape(str(nombre_proy))}</b>", styles["Title"]),
        Spacer(1, 12)
    ]

    if df_mat is None or df_mat.empty:
        elems.append(Paragraph("No se encontraron materiales.", styleN))
        doc.build(elems)
        return buffer.getvalue()

    df_agrupado = (
        df_mat.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"]
        .sum()
    )

    data = [["Material", "Unidad", "Cantidad"]]
    for _, row in df_agrupado.iterrows():
        data.append([
            Paragraph(formatear_material(row["Materiales"]), styleN),
            escape(str(row["Unidad"])),
            f"{float(row['Cantidad']):.2f}"
        ])

    tabla = Table(data, colWidths=[4 * inch, 1 * inch, 1 * inch])
    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    elems.append(tabla)
    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ==========================================================
# ANEXO: COSTOS DE MATERIALES (TABLA)
# ==========================================================
def tabla_costos_materiales_pdf(df_costos: pd.DataFrame):
    """
    Construye flowables ReportLab para el anexo de costos.
    Formato de moneda: "L 5.00"
    """
    titulo = Paragraph("ANEXO – Costos de Materiales", styles["Heading2"])

    if df_costos is None or df_costos.empty:
        return [titulo, Paragraph("No hay datos de costos disponibles.", styles["Normal"])]

    df = df_costos.copy()

    # ✅ NORMALIZAR columnas (ESTO ES LO QUE TE FALTABA)
    df.columns = [str(c).replace("\u00A0", " ").strip() for c in df.columns]

    # ✅ Aliases de columnas (por si vienen con otros nombres)
    ren = {}
    for c in df.columns:
        cc = c.lower().replace(" ", "_")
        if cc in {"material", "materiales", "descripcion", "descripción"}:
            ren[c] = "Materiales"
        elif cc in {"unidad", "unid"}:
            ren[c] = "Unidad"
        elif cc in {"cantidad", "qty"}:
            ren[c] = "Cantidad"
        elif cc in {"precio_unitario", "precio", "costo_unitario"}:
            ren[c] = "Precio Unitario"
        elif cc in {"costo", "costo_total", "costototal"}:
            ren[c] = "Costo Total"
    df = df.rename(columns=ren)

    # Columnas mínimas defensivas
    for c, default in [("Materiales", ""), ("Unidad", ""), ("Cantidad", 0.0), ("Precio Unitario", pd.NA), ("Costo Total", pd.NA)]:
        if c not in df.columns:
            df[c] = default

    # Asegurar numéricos
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0.0)
    df["Precio Unitario"] = pd.to_numeric(df["Precio Unitario"], errors="coerce")
    df["Costo Total"] = pd.to_numeric(df["Costo Total"], errors="coerce")

    # ✅ Tiene_Precio: mejor por >0 (no solo notna)
    df["Tiene_Precio"] = (df["Precio Unitario"].fillna(0.0) > 0)

    df = df.sort_values(["Tiene_Precio", "Materiales"], ascending=[False, True])

    subtotal = df.loc[df["Tiene_Precio"] == True, "Costo Total"].fillna(0.0).sum()

    def _money(v):
        if v is None or pd.isna(v):
            return ""
        return f"L {float(v):,.2f}"

    data = [["Materiales", "Unidad", "Cantidad", "Precio Unitario", "Costo Total"]]

    for _, r in df.iterrows():
        mat = str(r.get("Materiales", "") or "")
        uni = str(r.get("Unidad", "") or "")
        cant = float(r.get("Cantidad", 0) or 0)

        pu = r.get("Precio Unitario", None)
        ct = r.get("Costo Total", None)

        data.append([
            Paragraph(formatear_material(mat), styleN),
            escape(uni),
            f"{cant:,.2f}",
            _money(pu),
            _money(ct),
        ])

    data.append(["", "", "", "SUBTOTAL", _money(subtotal)])

    t = Table(
        data,
        repeatRows=1,
        colWidths=[3.7 * inch, 0.8 * inch, 0.9 * inch, 1.2 * inch, 1.2 * inch],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (1, 1), (1, -2), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (3, -1), (4, -1), "Helvetica-Bold"),
    ]))

    faltan = int((df["Tiene_Precio"] == False).sum())
    nota = Paragraph(
        f"Nota: {faltan} material(es) no tienen precio cargado.",
        styles["Normal"]
    )

    return [Spacer(1, 8), titulo, Spacer(1, 8), t, Spacer(1, 8), nota]

# ==========================================================
# ANEXO B: COSTOS POR ESTRUCTURA (TABLA)
# ==========================================================
def tabla_costos_estructuras_pdf(df_costos_estructuras: pd.DataFrame):
    """
    Construye flowables ReportLab para el ANEXO B – Costos por Estructura.

    Espera columnas (flexibles):
      - codigodeestructura (o Estructura)
      - Descripcion (o Descripción)
      - Cantidad
      - Costo Unitario
      - Costo Total

    Imprime moneda como "L 1,234.56"
    """
    titulo = Paragraph("ANEXO B – Costos por Estructura", styles["Heading2"])

    if df_costos_estructuras is None or df_costos_estructuras.empty:
        return [titulo, Paragraph("No hay datos de costos por estructura disponibles.", styles["Normal"])]

    df = df_costos_estructuras.copy()
    df.columns = [str(c).replace("\u00A0", " ").strip() for c in df.columns]

    # Normalizar nombres flexibles
    if "codigodeestructura" not in df.columns:
        if "Estructura" in df.columns:
            df["codigodeestructura"] = df["Estructura"]
        else:
            df["codigodeestructura"] = ""

    if "Descripcion" not in df.columns:
        if "Descripción" in df.columns:
            df["Descripcion"] = df["Descripción"]
        else:
            df["Descripcion"] = ""

    for col, default in [("Cantidad", 0), ("Costo Unitario", 0.0), ("Costo Total", 0.0)]:
        if col not in df.columns:
            df[col] = default

    # Tipos
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0).astype(int)
    df["Costo Unitario"] = pd.to_numeric(df["Costo Unitario"], errors="coerce").fillna(0.0)
    df["Costo Total"] = pd.to_numeric(df["Costo Total"], errors="coerce").fillna(0.0)

    # Orden
    df = df.sort_values(["codigodeestructura"], ascending=[True])

    # Helper moneda
    def _money(v):
        if v is None or pd.isna(v):
            return ""
        return f"L {float(v):,.2f}"

    # Encabezados
    data = [[
        "Estructura", "Descripción", "Cantidad", "Costo Unitario", "Costo Total"
    ]]

    for _, r in df.iterrows():
        cod = str(r.get("codigodeestructura", "") or "").strip()
        desc = str(r.get("Descripcion", "") or "").strip()
        cant = int(r.get("Cantidad", 0) or 0)

        data.append([
            Paragraph(escape(cod), styleN),
            Paragraph(escape(desc), styleN),
            f"{cant:d}",
            _money(r.get("Costo Unitario", 0.0)),
            _money(r.get("Costo Total", 0.0)),
        ])

    # Total general
    total_general = float(df["Costo Total"].sum())
    data.append(["", "", "", "TOTAL", _money(total_general)])

    t = Table(
        data,
        repeatRows=1,
        colWidths=[1.1 * inch, 3.1 * inch, 0.8 * inch, 1.2 * inch, 1.2 * inch],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 1), (2, -2), "CENTER"),
        ("ALIGN", (3, 1), (4, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (3, -1), (4, -1), "Helvetica-Bold"),
    ]))

    nota = Paragraph(
        "Nota: El costo por estructura se calcula como la suma de (cantidad_material × precio_unitario) "
        "para una (1) estructura, multiplicado por la cantidad total de esa estructura en el proyecto.",
        styles["Normal"]
    )

    return [Spacer(1, 8), titulo, Spacer(1, 8), t, Spacer(1, 8), nota]





# ==========================================================
# PDF: RESUMEN DE ESTRUCTURAS (GLOBAL)
# ==========================================================
def generar_pdf_estructuras_global(df_estructuras, nombre_proy):
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    def _safe_para(texto):
        t = "" if pd.isna(texto) else str(texto)
        t = escape(t)
        t = t.replace("-", "-\u200b").replace("/", "/\u200b").replace("_", "_\u200b")
        return t

    elems = [
        Paragraph(f"<b>Resumen de Estructuras - Proyecto: {escape(str(nombre_proy))}</b>", styles["Title"]),
        Spacer(1, 10)
    ]

    if df_estructuras is None or df_estructuras.empty:
        elems.append(Paragraph("No se encontraron estructuras.", styleN))
        doc.build(elems)
        return buffer.getvalue()

    st_hdr = ParagraphStyle("hdr_est", parent=styles["Normal"], fontName="Helvetica-Bold",
                            fontSize=9, leading=10, alignment=TA_CENTER)
    st_code = ParagraphStyle("code_est", parent=styles["Normal"], fontSize=8)
    st_desc = ParagraphStyle("desc_est", parent=styles["Normal"], fontSize=8, wordWrap="CJK")
    st_desc.splitLongWords = 1
    st_qty = ParagraphStyle("qty_est", parent=styles["Normal"], fontSize=8, alignment=TA_CENTER)

    ancho = doc.width * 0.98
    data = [[
        Paragraph("Estructura", st_hdr),
        Paragraph("Descripción", st_hdr),
        Paragraph("Cantidad", st_hdr),
    ]]

    for _, r in df_estructuras.iterrows():
        data.append([
            Paragraph(_safe_para(r.get("codigodeestructura", "")), st_code),
            Paragraph(_safe_para(r.get("Descripcion", "")), st_desc),
            Paragraph(_safe_para(r.get("Cantidad", "")), st_qty),
        ])

    tabla = Table(
        data,
        colWidths=[ancho * 0.18, ancho * 0.67, ancho * 0.15],
        repeatRows=1,
        hAlign="CENTER"
    )

    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 1), (2, -1), "CENTER"),
    ]))

    elems.append(tabla)
    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ==========================================================
# PDF: ESTRUCTURAS POR PUNTO
# ==========================================================
def generar_pdf_estructuras_por_punto(df_por_punto, nombre_proy):
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = [
        Paragraph(f"<b>Estructuras por Punto - Proyecto: {escape(str(nombre_proy))}</b>", styles["Title"]),
        Spacer(1, 12)
    ]

    if df_por_punto is None or df_por_punto.empty:
        elems.append(Paragraph("No se encontraron estructuras por punto.", styleN))
        doc.build(elems)
        return buffer.getvalue()

    puntos = sorted(
        df_por_punto["Punto"].unique(),
        key=lambda x: int(re.sub(r"\D", "", str(x)) or 0)
    )

    for p in puntos:
        m = re.search(r"(\d+)", str(p))
        num = m.group(1) if m else str(p)

        elems.append(Spacer(1, 6))
        elems.append(Paragraph(f"<b>Punto {escape(num)}</b>", styles["Heading2"]))

        df_p = df_por_punto[df_por_punto["Punto"] == p]

        data = [["Estructura", "Descripción", "Cantidad"]]
        for _, r in df_p.iterrows():
            data.append([
                escape(str(r.get("codigodeestructura", ""))),
                escape(str(r.get("Descripcion", ""))),
                escape(str(r.get("Cantidad", ""))),
            ])

        tabla = Table(data, colWidths=[1.5 * inch, 4 * inch, 1 * inch])
        tabla.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
            ("ALIGN", (2, 1), (2, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))

        elems.append(tabla)
        elems.append(Spacer(1, 0.2 * inch))

    doc.build(elems)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ==========================================================
# TABLA: ESTRUCTURAS POR PUNTO (USADA EN PDF COMPLETO)
# ==========================================================
def _tabla_estructuras_por_punto(punto, df_p, doc_width):
    st_hdr = ParagraphStyle("hdr", parent=styles["Normal"], fontName="Helvetica-Bold",
                            fontSize=9, alignment=TA_CENTER)
    st_code = ParagraphStyle("code", parent=styles["Normal"], fontSize=8)
    st_desc = ParagraphStyle("desc", parent=styles["Normal"], fontSize=8, wordWrap="CJK")
    st_desc.splitLongWords = 1
    st_qty = ParagraphStyle("qty", parent=styles["Normal"], fontSize=8, alignment=TA_CENTER)

    data = [[
        Paragraph("Estructura", st_hdr),
        Paragraph("Descripción", st_hdr),
        Paragraph("Cantidad", st_hdr)
    ]]

    for _, r in df_p.iterrows():
        data.append([
            Paragraph(escape(str(r.get("codigodeestructura", ""))), st_code),
            Paragraph(escape(str(r.get("Descripcion", ""))), st_desc),
            Paragraph(escape(str(r.get("Cantidad", ""))), st_qty),
        ])

    t = Table(
        data,
        colWidths=[doc_width * 0.20, doc_width * 0.65, doc_width * 0.15],
        repeatRows=1
    )

    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    return t


# ==========================================================
# PDF: MATERIALES POR PUNTO
# ==========================================================
def generar_pdf_materiales_por_punto(df_por_punto, nombre_proy):
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = [
        Paragraph(f"<b>Materiales por Punto - Proyecto: {escape(str(nombre_proy))}</b>", styles["Title"]),
        Spacer(1, 12),
    ]

    if df_por_punto is None or df_por_punto.empty:
        elems.append(Paragraph("No se encontraron materiales por punto.", styleN))
        doc.build(elems)
        return buffer.getvalue()

    puntos = sorted(
        df_por_punto["Punto"].unique(),
        key=lambda x: int(re.search(r"\d+", str(x)).group(0)) if re.search(r"\d+", str(x)) else 0
    )

    for p in puntos:
        m = re.search(r"(\d+)", str(p))
        num = m.group(1) if m else str(p)

        elems.append(Paragraph(f"<b>Punto {escape(num)}</b>", styles["Heading2"]))

        df_p = df_por_punto[df_por_punto["Punto"] == p]
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
        ]))

        elems.append(tabla)
        elems.append(Spacer(1, 0.2 * inch))

    doc.build(elems)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ==========================================================
# PDF COMPLETO (EL PRINCIPAL)
# ==========================================================
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
    - Resumen de Materiales (global)  (SIN precios)
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
        tabla = _tabla_estructuras_por_punto("GLOBAL", dfe, doc.width)
        elems.append(tabla)
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

    # ---------------------------
    # ANEXO B: Costos por Estructura
    # ---------------------------
    if df_costos_estructuras is not None and hasattr(df_costos_estructuras, "empty") and not df_costos_estructuras.empty:
        salto_pagina_seguro(elems)
        elems = extender_flowables(elems, tabla_costos_estructuras_pdf(df_costos_estructuras))


    
    # ---------------------------
    # Construcción final del PDF
    # ---------------------------
    quitar_saltos_finales(elems)
    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes




