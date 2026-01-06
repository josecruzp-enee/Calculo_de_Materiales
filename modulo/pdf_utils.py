# -*- coding: utf-8 -*-
"""
pdf_utils.py
Generación de informes PDF del cálculo de materiales y estructuras
Autor: José Nikol Cruz
"""

from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, PageBreak)
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from datetime import datetime
from io import BytesIO
import os
import re
import pandas as pd
from xml.sax.saxutils import escape

# --- Importación de tabla de cables ---
from modulo.configuracion_cables import tabla_cables_pdf

# ======== ESTILOS COMUNES ========
styles = getSampleStyleSheet()
styleN = ParagraphStyle(name="Normal9", parent=styles["Normal"], fontSize=9, leading=11)
styleH = styles["Heading1"]

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# ==========================================================
# ✅ FIX: formatear_material (IDENTIDAD)
# ==========================================================
def formatear_material(nombre):
    """
    Ya NO formatea (porque tu catálogo base ya está normalizado).
    Solo convierte a texto seguro para Paragraph.
    """
    if nombre is None or (isinstance(nombre, float) and pd.isna(nombre)):
        return ""
    return escape(str(nombre).strip())


# ==========================
# HELPERS (ANTI PÁGINAS EN BLANCO)
# ==========================
def safe_page_break(elems):
    """Agrega PageBreak solo si el último elemento NO es PageBreak."""
    if elems and not isinstance(elems[-1], PageBreak):
        elems.append(PageBreak())


def extend_flowables(elems, extra):
    """Extiende evitando doble PageBreak entre listas."""
    if not extra:
        return elems
    if elems and isinstance(elems[-1], PageBreak) and isinstance(extra[0], PageBreak):
        extra = extra[1:]
    elems.extend(extra)
    return elems


def strip_trailing_pagebreaks(elems):
    """Elimina PageBreak al final (evita página en blanco final)."""
    while elems and isinstance(elems[-1], PageBreak):
        elems.pop()
    return elems


# === Fondo para todas las páginas ===
def fondo_pagina(canvas, doc):
    try:
        canvas.saveState()
        fondo = os.path.join(BASE_DIR, "data", "Imagen Encabezado.jpg")
        ancho, alto = letter
        if os.path.exists(fondo):
            canvas.drawImage(fondo, 0, 0, width=ancho, height=alto, mask="auto")
        canvas.restoreState()
    except Exception as e:
        print(f"⚠️ Error aplicando fondo: {e}")


# ==========================================================
# ✅ NUEVO: Calibres desde tabla de Cables (sin longitudes)
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
      MT, BT, N, HP, RETENIDA
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


def hoja_info_proyecto(datos_proyecto, df_estructuras=None, df_mat=None):
    from math import sqrt

    def float_safe(x, d=0.0):
        try:
            return float(x)
        except Exception:
            return d

    def formato_tension(vll):
        """34.5 -> '19.9 LN / 34.5 LL KV'."""
        try:
            vll = float(vll)
            vln = round(vll / sqrt(3), 1)
            return f"{vln} LN / {vll} LL KV"
        except Exception:
            return str(vll)

    elems = []
    elems.append(Paragraph("<b>Hoja de Información del Proyecto</b>", styleH))
    elems.append(Spacer(1, 12))

    # ==== DATOS DEL PROYECTO ====
    descripcion_manual = datos_proyecto.get("descripcion_proyecto", "").strip()
    tension_valor = datos_proyecto.get("nivel_de_tension") or datos_proyecto.get("tension") or ""
    nivel_tension_fmt = formato_tension(tension_valor)

    cables = datos_proyecto.get("cables_proyecto", []) or []

    primarios = [c for c in cables if str(c.get("Tipo", "")).upper() == "MT"]
    secundarios = [c for c in cables if str(c.get("Tipo", "")).upper() in ("BT", "HP", "N")]
    retenidas = [c for c in cables if str(c.get("Tipo", "")).upper() == "RETENIDA"]

    calibre_primario_tab = _calibres_por_tipo(cables, "MT")
    calibre_secundario_tab = _calibres_por_tipo(cables, "BT")
    calibre_neutro_tab = _calibres_por_tipo(cables, "N")
    calibre_piloto_tab = _calibres_por_tipo(cables, "HP")
    calibre_retenidas_tab = _calibres_por_tipo(cables, "RETENIDA")

    calibre_primario = calibre_primario_tab or datos_proyecto.get("calibre_primario") or datos_proyecto.get("calibre_mt", "")
    calibre_secundario = calibre_secundario_tab or datos_proyecto.get("calibre_secundario", "")
    calibre_neutro = calibre_neutro_tab or datos_proyecto.get("calibre_neutro", "")
    calibre_piloto = calibre_piloto_tab or datos_proyecto.get("calibre_piloto", "")
    calibre_retenidas = calibre_retenidas_tab or datos_proyecto.get("calibre_retenidas", "")

    data = [
        ["Nombre del Proyecto:", datos_proyecto.get("nombre_proyecto", "")],
        ["Código / Expediente:", datos_proyecto.get("codigo_proyecto", "")],
        ["Nivel de Tensión (kV):", nivel_tension_fmt],
        ["Calibre Primario:", calibre_primario],
        ["Calibre Secundario:", calibre_secundario],
        ["Calibre Neutro:", calibre_neutro],
        ["Calibre Piloto:", calibre_piloto],
        ["Calibre Cable de Retenidas:", calibre_retenidas],
        ["Fecha de Informe:", datos_proyecto.get("fecha_informe", datetime.today().strftime("%Y-%m-%d"))],
        ["Responsable / Diseñador:", datos_proyecto.get("responsable", "N/A")],
        ["Empresa / Área:", datos_proyecto.get("empresa", "N/A")],
    ]

    tabla = Table(data, colWidths=[180, 300])
    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
    ]))

    elems.append(tabla)
    elems.append(Spacer(1, 18))

    # ==== DESCRIPCIÓN GENERAL ====
    lineas = []

    # --- Postes ---
    if df_estructuras is not None and not df_estructuras.empty:
        postes = df_estructuras[
            df_estructuras["codigodeestructura"].str.contains("PC|PT", case=False, na=False)
        ]
        if not postes.empty:
            resumen = {}
            for _, r in postes.iterrows():
                cod = r["codigodeestructura"]
                cant = int(r["Cantidad"])
                resumen[cod] = resumen.get(cod, 0) + cant

            partes = [f"{v} {k}" for k, v in resumen.items()]
            total = sum(resumen.values())
            lineas.append(f"Hincado de {', '.join(partes)} (Total: {total} postes).")

    # --- Primarios (LP) ---
    for c in primarios:
        long_total = float_safe(c.get("Total Cable (m)", c.get("Longitud (m)", 0)))
        fase = str(c.get("Configuración", "")).strip().upper()
        calibre = str(c.get("Calibre", "")).strip()

        m = re.search(r"(\d+)\s*F", fase)
        n_fases = int(m.group(1)) if m else 1
        long_desc = (long_total / n_fases) if n_fases > 1 else long_total

        if long_desc > 0 and calibre:
            lineas.append(
                f"Construcción de {long_desc:.0f} m de LP, {nivel_tension_fmt}, {fase}, {calibre}."
            )

    # --- Secundarios (LS) ---
    for c in secundarios:
        long_total = float_safe(c.get("Total Cable (m)", 0))
        fase = str(c.get("Configuración", "")).strip().upper()
        calibre = str(c.get("Calibre", "")).strip()

        m = re.search(r"(\d+)\s*F", fase)
        n_fases = int(m.group(1)) if m else 1
        long_desc = (long_total / n_fases) if n_fases > 1 else long_total

        if long_desc > 0 and calibre:
            lineas.append(
                f"Construcción de {long_desc:.0f} m de LS, 120/240 V, {fase}, {calibre}."
            )

    # --- Transformadores (TS/TD/TT) ---
    if df_mat is not None and not df_mat.empty:
        s = df_mat["Materiales"].astype(str)

        # Detecta: TS-37.5KVA, TS-37.5 KVA, TD-50KVA, TT-75 KVA, etc.
        mask_tx = s.str.contains(
            r"\b(TS|TD|TT)\s*-\s*(\d+(?:\.\d+)?)\s*KVA\b",
            case=False, na=False, regex=True
        )
        transf = df_mat[mask_tx].copy()

        if not transf.empty:
            transf["Cantidad"] = pd.to_numeric(transf["Cantidad"], errors="coerce").fillna(0)

            # Clave normalizada (para que si viene repetido por 3F no se sume 3 veces)
            ext = transf["Materiales"].astype(str).str.extract(
                r"\b(TS|TD|TT)\s*-\s*(\d+(?:\.\d+)?)\s*KVA\b",
                flags=re.IGNORECASE
            )
            transf["_key"] = ext[0].str.upper() + "-" + ext[1] + " KVA"

            # Tomar MAX por cada tipo/capacidad (evita triplicación)
            bancos = transf.groupby("_key", as_index=False)["Cantidad"].max()

            mult = {"TS": 1, "TD": 2, "TT": 3}

            total_t = 0
            for _, r in bancos.iterrows():
                pref = str(r["_key"]).split("-")[0].upper()  # TS / TD / TT
                total_t += float_safe(r["Cantidad"], 0) * mult.get(pref, 1)

            capacidades = ", ".join(bancos["_key"].tolist())
            lineas.append(f"Instalación de {int(total_t)} transformador(es) ({capacidades}).")

    # --- Luminarias ---
    if df_mat is not None and not df_mat.empty:
        lums = df_mat[df_mat["Materiales"].str.contains("Lámpara|Lampara|Alumbrado", case=False, na=False)]
        if not lums.empty:
            total_l = lums["Cantidad"].sum()
            lineas.append(f"Instalación de {int(total_l)} luminaria(s) de alumbrado público.")

    descripcion_auto = "<br/>".join([f"{i + 1}. {l}" for i, l in enumerate(lineas)])
    cuerpo_desc = (descripcion_manual + "<br/><br/>" + descripcion_auto) if descripcion_manual else descripcion_auto

    elems.append(Paragraph("<b>Descripción general del Proyecto:</b>", styleN))
    elems.append(Spacer(1, 6))
    elems.append(Paragraph(cuerpo_desc, styleN))
    elems.append(Spacer(1, 18))

    return elems




# === Generar PDF de materiales globales ===
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

    df_agrupado = df_mat.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
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
    ]))
    elems.append(tabla)

    doc.build(elems)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# === Generar estructuras global ===
def generar_pdf_estructuras_global(df_estructuras, nombre_proy):
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    def _safe_para(texto):
        t = "" if pd.isna(texto) else str(texto)
        t = escape(t)
        t = t.replace("-", "-\u200b")
        return t

    elems = [
        Paragraph(f"<b>Resumen de Estructuras - Proyecto: {escape(str(nombre_proy))}</b>", styles["Title"]),
        Spacer(1, 12)
    ]

    st_hdr = ParagraphStyle(
        "hdr_est", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=9, leading=10, alignment=TA_CENTER
    )
    st_code = ParagraphStyle(
        "code_est", parent=styles["Normal"], fontName="Helvetica",
        fontSize=8, leading=9, alignment=TA_LEFT
    )
    st_desc = ParagraphStyle(
        "desc_est", parent=styles["Normal"], fontName="Helvetica",
        fontSize=8, leading=9, alignment=TA_LEFT, wordWrap="CJK"
    )
    st_desc.splitLongWords = 1
    st_desc.spaceShrinkage = 0.05

    st_qty = ParagraphStyle(
        "qty_est", parent=styles["Normal"], fontName="Helvetica",
        fontSize=8, leading=9, alignment=TA_CENTER
    )

    w1 = doc.width * 0.18
    w2 = doc.width * 0.67
    w3 = doc.width * 0.15

    data = [[
        Paragraph("Estructura", st_hdr),
        Paragraph("Descripción", st_hdr),
        Paragraph("Cantidad", st_hdr),
    ]]

    for _, row in df_estructuras.iterrows():
        data.append([
            Paragraph(_safe_para(row.get("codigodeestructura", "")), st_code),
            Paragraph(_safe_para(row.get("Descripcion", "")), st_desc),
            Paragraph(_safe_para(row.get("Cantidad", "")), st_qty),
        ])

    tabla = Table(data, colWidths=[w1, w2, w3], repeatRows=1, hAlign="LEFT")
    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 1), (2, -1), "CENTER"),
        ("WORDWRAP", (1, 1), (1, -1), "CJK"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    elems.append(tabla)

    doc.build(elems)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# === Generar estructuras por punto ===
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

    puntos = sorted(df_por_punto["Punto"].unique(), key=lambda x: int(re.sub(r"\D", "", str(x)) or 0))

    for p in puntos:
        s = str(p).strip()
        m = re.search(r"(\d+)", s)
        num = m.group(1) if m else s

        elems.append(Spacer(1, 6))
        elems.append(Paragraph(f"<b>Punto {escape(str(num))}</b>", styles["Heading2"]))

        df_p = df_por_punto[df_por_punto["Punto"] == p]
        data = [["Estructura", "Descripción", "Cantidad"]]

        for _, row in df_p.iterrows():
            data.append([
                escape(str(row.get("codigodeestructura", ""))),
                escape(str(row.get("Descripcion", ""))),
                escape(str(row.get("Cantidad", "")))
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


# === Materiales adicionales ===
def agregar_tabla_materiales_adicionales(elems, datos_proyecto):
    df_extra = datos_proyecto.get("materiales_extra")
    if df_extra is None or df_extra.empty:
        return elems

    safe_page_break(elems)
    elems.append(Paragraph("<b>Materiales Adicionales</b>", styles["Heading2"]))
    elems.append(Spacer(1, 12))

    data_extra = [["Material", "Unidad", "Cantidad"]]
    for _, row in df_extra.iterrows():
        data_extra.append([
            escape(str(row.get("Materiales", ""))),
            escape(str(row.get("Unidad", ""))),
            f"{float(row.get('Cantidad', 0)):.2f}"
        ])

    tabla = Table(data_extra, colWidths=[4 * inch, 1 * inch, 1 * inch])
    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.orange),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke)
    ]))
    elems.append(tabla)
    return elems


# === Generar PDF de Materiales por Punto ===
def generar_pdf_materiales_por_punto(df_por_punto, nombre_proy):
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="con_fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = []
    elems.append(Paragraph(f"<b>Materiales por Punto - Proyecto: {escape(str(nombre_proy))}</b>", styles["Title"]))
    elems.append(Spacer(1, 12))

    puntos = sorted(
        df_por_punto["Punto"].unique(),
        key=lambda x: int(re.search(r"\d+", str(x)).group(0)) if re.search(r"\d+", str(x)) else 0
    )

    for p in puntos:
        s = str(p).strip()
        m = re.search(r"(\d+)", s)
        num = str(int(m.group(1))) if m else s

        elems.append(Paragraph(f"<b>Punto {escape(str(num))}</b>", styles["Heading2"]))

        df_p = df_por_punto[df_por_punto["Punto"] == p]
        df_agrupado = df_p.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

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
            ("BACKGROUND", (0, 0), (-1, 0), colors.darkgreen),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))

        elems.append(tabla)
        elems.append(Spacer(1, 0.2 * inch))

    doc.build(elems)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def _tabla_estructuras_por_punto(punto: str, df_p: pd.DataFrame, doc_width: float):
    st_hdr = ParagraphStyle(
        "hdr", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=9, leading=10, alignment=TA_CENTER
    )

    st_code = ParagraphStyle(
        "code", parent=styles["Normal"], fontName="Helvetica",
        fontSize=8, leading=9, alignment=TA_LEFT
    )

    st_desc = ParagraphStyle(
        "desc", parent=styles["Normal"], fontName="Helvetica",
        fontSize=8, leading=9, alignment=TA_LEFT, wordWrap="CJK"
    )
    st_desc.splitLongWords = 1

    st_qty = ParagraphStyle(
        "qty", parent=styles["Normal"], fontName="Helvetica",
        fontSize=8, leading=9, alignment=TA_CENTER
    )

    w1 = doc_width * 0.20
    w2 = doc_width * 0.65
    w3 = doc_width * 0.15

    data = [[
        Paragraph("Estructura", st_hdr),
        Paragraph("Descripción", st_hdr),
        Paragraph("Cantidad", st_hdr)
    ]]

    for _, row in df_p.iterrows():
        data.append([
            Paragraph(escape(str(row.get("codigodeestructura", ""))), st_code),
            Paragraph(escape(str(row.get("Descripcion", ""))), st_desc),
            Paragraph(escape(str(row.get("Cantidad", ""))), st_qty),
        ])

    t = Table(data, colWidths=[w1, w2, w3], repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def generar_pdf_completo(df_mat, df_estructuras, df_estructuras_por_punto, df_mat_por_punto, datos_proyecto):
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = []

    elems = extend_flowables(elems, hoja_info_proyecto(datos_proyecto, df_estructuras, df_mat))
    safe_page_break(elems)

    elems.append(Paragraph("<b>Resumen de Materiales</b>", styles["Heading2"]))

    df_agr = (
        df_mat.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
        if not df_mat.empty
        else pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])
    )

    # === Agregar los cables del proyecto al resumen de materiales ===
    if "cables_proyecto" in datos_proyecto and datos_proyecto["cables_proyecto"]:
        for cable in datos_proyecto["cables_proyecto"]:
            tipo = cable.get("Tipo", "")
            calibre = cable.get("Calibre", "")
            longitud = cable.get("Total Cable (m)", cable.get("Longitud (m)", 0))
            if longitud and calibre:
                descripcion = f"Cable {tipo} {calibre}"
                df_agr.loc[len(df_agr)] = [descripcion, "m", float(longitud)]

    data = [["Material", "Unidad", "Cantidad"]]
    for _, r in df_agr.iterrows():
        data.append([
            Paragraph(formatear_material(r["Materiales"]), styleN),
            escape(str(r["Unidad"])),
            f"{float(r['Cantidad']):.2f}"
        ])

    tabla = Table(data, colWidths=[4 * inch, 1 * inch, 1 * inch])
    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
    ]))
    elems.append(tabla)
    safe_page_break(elems)

    elems = agregar_tabla_materiales_adicionales(elems, datos_proyecto)
    elems = extend_flowables(elems, tabla_cables_pdf(datos_proyecto))

    if not df_estructuras.empty:
        safe_page_break(elems)
        elems.append(Paragraph("<b>Resumen de Estructuras</b>", styles["Heading2"]))

        data_estruct = [["Estructura", "Descripción", "Cantidad"]]
        for _, row in df_estructuras.iterrows():
            data_estruct.append([
                escape(str(row.get("codigodeestructura", ""))),
                escape(str(row.get("Descripcion", ""))),
                escape(str(row.get("Cantidad", "")))
            ])

        tabla_estruct = Table(data_estruct, colWidths=[1.5 * inch, 4 * inch, 1 * inch])
        tabla_estruct.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (2, 1), (2, -1), "CENTER")
        ]))
        elems.append(tabla_estruct)

    if not df_estructuras_por_punto.empty:
        safe_page_break(elems)
        elems.append(Paragraph("<b>Estructuras por Punto</b>", styles["Heading2"]))

        puntos = sorted(
            df_estructuras_por_punto["Punto"].unique(),
            key=lambda x: int(re.sub(r"\D", "", str(x)) or 0)
        )

        for p in puntos:
            s = str(p).strip()
            m = re.search(r"(\d+)", s)
            num = str(int(m.group(1))) if m else s

            elems.append(Paragraph(f"<b>Punto {escape(str(num))}</b>", styles["Heading3"]))

            df_p = df_estructuras_por_punto[df_estructuras_por_punto["Punto"] == p]
            tabla_p = _tabla_estructuras_por_punto(num, df_p, doc.width)

            elems.append(tabla_p)
            elems.append(Spacer(1, 0.2 * inch))

    if not df_mat_por_punto.empty:
        safe_page_break(elems)
        elems.append(Paragraph("<b>Materiales por Punto</b>", styles["Heading2"]))

        puntos = sorted(
            df_mat_por_punto["Punto"].unique(),
            key=lambda x: int(re.search(r"\d+", str(x)).group(0)) if re.search(r"\d+", str(x)) else 0
        )

        for p in puntos:
            s = str(p).strip()
            m = re.search(r"(\d+)", s)
            num = str(int(m.group(1))) if m else s

            elems.append(Paragraph(f"<b>Punto {escape(str(num))}</b>", styles["Heading3"]))

            df_p = df_mat_por_punto[df_mat_por_punto["Punto"] == p]
            df_agr_p = df_p.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

            data = [["Material", "Unidad", "Cantidad"]]
            for _, r in df_agr_p.iterrows():
                data.append([
                    Paragraph(formatear_material(r["Materiales"]), styleN),
                    escape(str(r["Unidad"])),
                    f"{float(r['Cantidad']):.2f}"
                ])

            tabla_m = Table(data, colWidths=[4 * inch, 1 * inch, 1 * inch])
            tabla_m.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.darkgreen),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (1, 1), (-1, -1), "CENTER")
            ]))

            elems.append(tabla_m)
            elems.append(Spacer(1, 0.2 * inch))

    strip_trailing_pagebreaks(elems)

    doc.build(elems)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes





