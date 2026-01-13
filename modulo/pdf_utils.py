# -*- coding: utf-8 -*-
"""
pdf_utils.py
Generación de informes PDF del cálculo de materiales y estructuras
Autor: José Nikol Cruz
"""

from __future__ import annotations

from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
    Table, TableStyle, PageBreak
)
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

from modulo.configuracion_cables import tabla_cables_pdf


# ==========================================================
# ESTILOS
# ==========================================================
styles = getSampleStyleSheet()
styleN = ParagraphStyle(name="Normal9", parent=styles["Normal"], fontSize=9, leading=11)
styleH = styles["Heading1"]

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# ==========================================================
# HELPERS ANTI PÁGINAS EN BLANCO
# ==========================================================
def safe_page_break(elems: list) -> None:
    if elems and not isinstance(elems[-1], PageBreak):
        elems.append(PageBreak())


def extend_flowables(elems: list, extra: list) -> list:
    if not extra:
        return elems
    if elems and isinstance(elems[-1], PageBreak) and isinstance(extra[0], PageBreak):
        extra = extra[1:]
    elems.extend(extra)
    return elems


def strip_trailing_pagebreaks(elems: list) -> list:
    while elems and isinstance(elems[-1], PageBreak):
        elems.pop()
    return elems


# ==========================================================
# HELPERS TEXTO (CLAVE: NO DAÑAR º / ° EN DESCRIPCIONES)
# ==========================================================
def normalizar_texto_pdf(txt: object) -> str:
    """Solo para códigos/materiales (guiones raros desde Excel)."""
    if txt is None or (isinstance(txt, float) and pd.isna(txt)):
        return ""
    s = str(txt)
    s = (s.replace("–", "-")
           .replace("—", "-")
           .replace("−", "-")
           .replace("‐", "-"))
    s = s.replace("\u00A0", " ")
    return s.strip()


def _safe_para_desc(texto: object) -> str:
    """Para DESCRIPCIONES: NO normaliza símbolos como º."""
    if texto is None or (isinstance(texto, float) and pd.isna(texto)):
        return ""
    t = escape(str(texto).strip())
    t = t.replace("-", "-\u200b").replace("/", "/\u200b").replace("_", "_\u200b")
    return t


def _safe_para_norm(texto: object) -> str:
    """Para CÓDIGOS/MATERIALES: sí normaliza guiones raros."""
    t = normalizar_texto_pdf(texto)
    t = escape(t)
    t = t.replace("-", "-\u200b").replace("/", "/\u200b").replace("_", "_\u200b")
    return t


def float_safe(x, d: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return d


def formatear_material(nombre) -> str:
    """Catálogo ya normalizado: solo escape."""
    if nombre is None or (isinstance(nombre, float) and pd.isna(nombre)):
        return ""
    return escape(str(nombre).strip())


# ==========================================================
# DOC + FONDO
# ==========================================================
def fondo_pagina(canvas, doc) -> None:
    try:
        canvas.saveState()
        fondo = os.path.join(BASE_DIR, "data", "Imagen Encabezado.jpg")
        ancho, alto = letter
        if os.path.exists(fondo):
            canvas.drawImage(fondo, 0, 0, width=ancho, height=alto, mask="auto")
        canvas.restoreState()
    except Exception as e:
        print(f"⚠️ Error aplicando fondo: {e}")


def crear_doc(buffer: BytesIO) -> BaseDocTemplate:
    doc = BaseDocTemplate(buffer, pagesize=letter)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])
    return doc


# ==========================================================
# CABLES: calibres únicos por tipo
# ==========================================================
def _dedupe_keep_order(vals):
    seen = set()
    out = []
    for v in vals:
        k = str(v).strip().upper()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(str(v).strip())
    return out


def _calibres_por_tipo(cables, tipo_buscar: str) -> str:
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
    return ", ".join(_dedupe_keep_order(calibres))


def _formato_tension(vll) -> str:
    from math import sqrt, floor
    try:
        vll = float(vll)
        vln = vll / sqrt(3)
        vln = floor(vln * 10) / 10
        return f"{vln:.1f} LN / {vll:.1f} LL KV"
    except Exception:
        return str(vll)


# ==========================================================
# TABLAS REUSABLES
# ==========================================================
def tabla_resumen_materiales(df_mat_agr: pd.DataFrame) -> Table:
    data = [["Material", "Unidad", "Cantidad"]]
    for _, r in df_mat_agr.iterrows():
        data.append([
            Paragraph(formatear_material(r["Materiales"]), styleN),
            escape(str(r["Unidad"])),
            f"{float_safe(r['Cantidad'], 0):.2f}",
        ])

    t = Table(data, colWidths=[4 * inch, 1 * inch, 1 * inch])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
    ]))
    return t


def tabla_resumen_estructuras(df_estructuras: pd.DataFrame, doc_width: float) -> Table:
    st_hdr = ParagraphStyle("hdr_est", parent=styles["Normal"], fontName="Helvetica-Bold",
                            fontSize=9, leading=10, alignment=TA_CENTER)
    st_code = ParagraphStyle("code_est", parent=styles["Normal"], fontName="Helvetica",
                             fontSize=8, leading=9, alignment=TA_LEFT)
    st_desc = ParagraphStyle("desc_est", parent=styles["Normal"], fontName="Helvetica",
                             fontSize=8, leading=9, alignment=TA_LEFT, wordWrap="CJK")
    st_desc.splitLongWords = 1
    st_qty = ParagraphStyle("qty_est", parent=styles["Normal"], fontName="Helvetica",
                            fontSize=8, leading=9, alignment=TA_CENTER)

    ancho_util = doc_width * 0.98
    w1, w2, w3 = ancho_util * 0.18, ancho_util * 0.67, ancho_util * 0.15

    data = [[
        Paragraph("Estructura", st_hdr),
        Paragraph("Descripción", st_hdr),
        Paragraph("Cantidad", st_hdr),
    ]]

    for _, row in df_estructuras.iterrows():
        data.append([
            Paragraph(_safe_para_norm(row.get("codigodeestructura", "")), st_code),
            Paragraph(_safe_para_desc(row.get("Descripcion", "")), st_desc),
            Paragraph(_safe_para_norm(row.get("Cantidad", "")), st_qty),
        ])

    t = Table(data, colWidths=[w1, w2, w3], repeatRows=1, hAlign="CENTER")
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 1), (2, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEADING", (0, 0), (-1, -1), 9),
    ]))
    return t


def tabla_estructuras_por_punto(df_p: pd.DataFrame, doc_width: float) -> Table:
    st_hdr = ParagraphStyle("hdr_p", parent=styles["Normal"], fontName="Helvetica-Bold",
                            fontSize=9, leading=10, alignment=TA_CENTER)
    st_code = ParagraphStyle("code_p", parent=styles["Normal"], fontName="Helvetica",
                             fontSize=8, leading=9, alignment=TA_LEFT)
    st_desc = ParagraphStyle("desc_p", parent=styles["Normal"], fontName="Helvetica",
                             fontSize=8, leading=9, alignment=TA_LEFT, wordWrap="CJK")
    st_desc.splitLongWords = 1
    st_qty = ParagraphStyle("qty_p", parent=styles["Normal"], fontName="Helvetica",
                            fontSize=8, leading=9, alignment=TA_CENTER)

    w1, w2, w3 = doc_width * 0.20, doc_width * 0.65, doc_width * 0.15

    data = [[
        Paragraph("Estructura", st_hdr),
        Paragraph("Descripción", st_hdr),
        Paragraph("Cantidad", st_hdr),
    ]]

    for _, row in df_p.iterrows():
        data.append([
            Paragraph(_safe_para_norm(row.get("codigodeestructura", "")), st_code),
            Paragraph(_safe_para_desc(row.get("Descripcion", "")), st_desc),
            Paragraph(_safe_para_norm(row.get("Cantidad", "")), st_qty),
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


# ==========================================================
# SECCIÓN: MATERIALES ADICIONALES
# ==========================================================
def agregar_tabla_materiales_adicionales(elems: list, datos_proyecto: dict) -> list:
    df_extra = datos_proyecto.get("materiales_extra")
    if df_extra is None or df_extra.empty:
        return elems

    safe_page_break(elems)
    elems.append(Paragraph("<b>Materiales Adicionales</b>", styles["Heading2"]))
    elems.append(Spacer(1, 12))

    st_mat = ParagraphStyle("mat_wrap", parent=styles["Normal"], fontName="Helvetica",
                            fontSize=8, leading=9, alignment=TA_LEFT, wordWrap="CJK")
    st_mat.splitLongWords = 1

    st_mid = ParagraphStyle("mid", parent=styles["Normal"], fontName="Helvetica",
                            fontSize=8, leading=9, alignment=TA_CENTER)

    data_extra = [[
        Paragraph("<b>Material</b>", st_mid),
        Paragraph("<b>Unidad</b>", st_mid),
        Paragraph("<b>Cantidad</b>", st_mid),
    ]]

    for _, row in df_extra.iterrows():
        mat = escape(str(row.get("Materiales", "")).strip())
        uni = escape(str(row.get("Unidad", "")).strip())
        cant = float_safe(row.get("Cantidad", 0), 0)

        data_extra.append([
            Paragraph(mat, st_mat),
            Paragraph(uni, st_mid),
            Paragraph(f"{cant:.2f}", st_mid),
        ])

    t = Table(data_extra, colWidths=[4 * inch, 1 * inch, 1 * inch])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.orange),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("WORDWRAP", (0, 1), (0, -1), "CJK"),
    ]))

    elems.append(t)
    return elems


# ==========================================================
# SECCIÓN: HOJA INFO PROYECTO (TU LÓGICA, PERO ORDENADA)
# ==========================================================
def hoja_info_proyecto(datos_proyecto: dict, df_estructuras=None, df_mat=None) -> list:
    elems = []
    elems.append(Paragraph("<b>Hoja de Información del Proyecto</b>", styleH))
    elems.append(Spacer(1, 12))

    descripcion_manual = str(datos_proyecto.get("descripcion_proyecto", "") or "").strip()
    tension_valor = datos_proyecto.get("nivel_de_tension") or datos_proyecto.get("tension") or ""
    nivel_tension_fmt = _formato_tension(tension_valor)

    cables = datos_proyecto.get("cables_proyecto", []) or []
    primarios = [c for c in cables if str(c.get("Tipo", "")).upper() == "MT"]
    secundarios = [c for c in cables if str(c.get("Tipo", "")).upper() in ("BT", "HP", "N")]

    data = [
        ["Nombre del Proyecto:", datos_proyecto.get("nombre_proyecto", "")],
        ["Código / Expediente:", datos_proyecto.get("codigo_proyecto", "")],
        ["Nivel de Tensión (kV):", nivel_tension_fmt],
        ["Calibre Primario:", _calibres_por_tipo(cables, "MT") or datos_proyecto.get("calibre_primario", "")],
        ["Calibre Secundario:", _calibres_por_tipo(cables, "BT") or datos_proyecto.get("calibre_secundario", "")],
        ["Calibre Neutro:", _calibres_por_tipo(cables, "N") or datos_proyecto.get("calibre_neutro", "")],
        ["Calibre Piloto:", _calibres_por_tipo(cables, "HP") or datos_proyecto.get("calibre_piloto", "")],
        ["Calibre Cable de Retenidas:", _calibres_por_tipo(cables, "RETENIDA") or datos_proyecto.get("calibre_retenidas", "")],
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

    # -------- Descripción general automática --------
    lineas = []

    # Postes
    if df_estructuras is not None and not df_estructuras.empty and "codigodeestructura" in df_estructuras.columns:
        postes = df_estructuras[df_estructuras["codigodeestructura"].astype(str).str.contains("PC|PT", case=False, na=False)]
        if not postes.empty:
            resumen = {}
            for _, r in postes.iterrows():
                cod = str(r.get("codigodeestructura", "")).strip()
                cant = int(float_safe(r.get("Cantidad", 0), 0))
                if cod:
                    resumen[cod] = resumen.get(cod, 0) + cant
            partes = [f"{v} {k}" for k, v in resumen.items()]
            total = sum(resumen.values())
            lineas.append(f"Hincado de {', '.join(partes)} (Total: {total} postes).")

    # Primarios
    for c in primarios:
        long_total = float_safe(c.get("Total Cable (m)", c.get("Longitud (m)", 0)))
        fase = str(c.get("Configuración", "")).strip().upper()
        calibre = str(c.get("Calibre", "")).strip()

        m = re.search(r"(\d+)\s*F", fase)
        n_fases = int(m.group(1)) if m else 1
        long_desc = (long_total / n_fases) if n_fases > 1 else long_total

        if long_desc > 0 and calibre:
            lineas.append(f"Construcción de {long_desc:.0f} m de LP, {nivel_tension_fmt}, {fase}, {calibre}.")

    # Secundarios
    for c in secundarios:
        long_total = float_safe(c.get("Total Cable (m)", 0))
        fase = str(c.get("Configuración", "")).strip().upper()
        calibre = str(c.get("Calibre", "")).strip()

        m = re.search(r"(\d+)\s*F", fase)
        n_fases = int(m.group(1)) if m else 1
        long_desc = (long_total / n_fases) if n_fases > 1 else long_total

        if long_desc > 0 and calibre:
            lineas.append(f"Construcción de {long_desc:.0f} m de LS, 120/240 V, {fase}, {calibre}.")

    # Transformadores (igual que tu lógica)
    total_t = 0
    capacidades = []
    mult = {"TS": 1, "TD": 2, "TT": 3}

    if df_estructuras is not None and not df_estructuras.empty and "codigodeestructura" in df_estructuras.columns:
        s = df_estructuras["codigodeestructura"].astype(str).str.upper().str.strip()
        ext = s.str.extract(r"^(TS|TD|TT)\s*-\s*(\d+(?:\.\d+)?)\s*KVA$", expand=True)
        mask = ext[0].notna()
        if mask.any():
            qty = pd.to_numeric(df_estructuras.loc[mask, "Cantidad"], errors="coerce").fillna(0)
            pref = ext.loc[mask, 0]
            kva = ext.loc[mask, 1]
            total_t = int((qty * pref.map(mult)).sum())
            capacidades = sorted({f"{p}-{k} KVA" for p, k in zip(pref, kva)})

    if total_t == 0 and df_mat is not None and not df_mat.empty and "Materiales" in df_mat.columns:
        s = df_mat["Materiales"].astype(str).str.upper().str.strip()
        ext = s.str.extract(r"\b(TS|TD|TT)\s*-\s*(\d+(?:\.\d+)?)\s*KVA\b", expand=True)
        mask = ext[0].notna()
        if mask.any():
            df_tx = df_mat.loc[mask].copy()
            df_tx["Cantidad"] = pd.to_numeric(df_tx["Cantidad"], errors="coerce").fillna(0)
            df_tx["_key"] = ext.loc[mask, 0] + "-" + ext.loc[mask, 1] + " KVA"
            bancos = df_tx.groupby("_key", as_index=False)["Cantidad"].max()

            total_t = 0
            for _, r in bancos.iterrows():
                pref = str(r["_key"]).split("-")[0].upper()
                total_t += float_safe(r["Cantidad"], 0) * mult.get(pref, 1)

            total_t = int(total_t)
            capacidades = bancos["_key"].tolist()

    if total_t > 0:
        cap_txt = ", ".join(capacidades) if capacidades else ""
        lineas.append(f"Instalación de {total_t} transformador(es) {f'({cap_txt})' if cap_txt else ''}.")

    # Luminarias (bien indentado)
    if df_mat is not None and not df_mat.empty and "Materiales" in df_mat.columns:
        lums = df_mat[df_mat["Materiales"].astype(str).str.contains("Lámpara|Lampara|Alumbrado|\\bLL-", case=False, na=False)].copy()
        if not lums.empty:
            lums["Cantidad"] = pd.to_numeric(lums.get("Cantidad", 0), errors="coerce").fillna(0)

            def pot(txt):
                s = normalizar_texto_pdf(txt).upper()
                m = re.search(r"(\d+)\s*A\s*(\d+)\s*W", s)
                if m:
                    return f"{m.group(1)}-{m.group(2)} W"
                m = re.search(r"(\d+)\s*-\s*(\d+)\s*W", s)
                if m:
                    return f"{m.group(1)}-{m.group(2)} W"
                m = re.search(r"(\d+)\s*W", s)
                if m:
                    return f"{m.group(1)} W"
                return "SIN POTENCIA"

            resumen = (lums.assign(Pot=lums["Materiales"].map(pot))
                          .groupby("Pot")["Cantidad"].sum()
                          .round().astype(int))

            total = int(resumen.sum())
            det = " y ".join([f"{v} de {k}" for k, v in resumen.items()])
            lineas.append(f"Instalación de {total} luminaria(s) de alumbrado público ({det}).")

    descripcion_auto = "<br/>".join([f"{i + 1}. {l}" for i, l in enumerate(lineas)])
    cuerpo_desc = (descripcion_manual + "<br/><br/>" + descripcion_auto) if descripcion_manual else descripcion_auto

    elems.append(Paragraph("<b>Descripción general del Proyecto:</b>", styleN))
    elems.append(Spacer(1, 6))
    elems.append(Paragraph(cuerpo_desc, styleN))
    elems.append(Spacer(1, 18))
    return elems


# ==========================================================
# PDFs INDIVIDUALES
# ==========================================================
def generar_pdf_materiales(df_mat: pd.DataFrame, nombre_proy: str) -> bytes:
    buffer = BytesIO()
    doc = crear_doc(buffer)

    elems = [
        Paragraph(f"<b>Resumen de Materiales - Proyecto: {escape(str(nombre_proy))}</b>", styles["Title"]),
        Spacer(1, 12)
    ]

    df_agr = df_mat.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
    elems.append(tabla_resumen_materiales(df_agr))

    doc.build(elems)
    out = buffer.getvalue()
    buffer.close()
    return out


def generar_pdf_estructuras_global(df_estructuras: pd.DataFrame, nombre_proy: str) -> bytes:
    buffer = BytesIO()
    doc = crear_doc(buffer)

    elems = [
        Paragraph(f"<b>Resumen de Estructuras - Proyecto: {escape(str(nombre_proy))}</b>", styles["Title"]),
        Spacer(1, 10),
        tabla_resumen_estructuras(df_estructuras, doc.width),
    ]

    doc.build(elems)
    out = buffer.getvalue()
    buffer.close()
    return out


def generar_pdf_estructuras_por_punto(df_por_punto: pd.DataFrame, nombre_proy: str) -> bytes:
    buffer = BytesIO()
    doc = crear_doc(buffer)

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
        elems.append(tabla_estructuras_por_punto(df_p, doc.width))
        elems.append(Spacer(1, 0.2 * inch))

    doc.build(elems)
    out = buffer.getvalue()
    buffer.close()
    return out


def generar_pdf_materiales_por_punto(df_por_punto: pd.DataFrame, nombre_proy: str) -> bytes:
    buffer = BytesIO()
    doc = crear_doc(buffer)

    elems = [
        Paragraph(f"<b>Materiales por Punto - Proyecto: {escape(str(nombre_proy))}</b>", styles["Title"]),
        Spacer(1, 12),
    ]

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
        df_agr = df_p.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

        elems.append(tabla_resumen_materiales(df_agr))
        elems.append(Spacer(1, 0.2 * inch))

    doc.build(elems)
    out = buffer.getvalue()
    buffer.close()
    return out


# ==========================================================
# PDF COMPLETO (ORQUESTADOR LIMPIO)
# ==========================================================
def generar_pdf_completo(
    df_mat: pd.DataFrame,
    df_estructuras: pd.DataFrame,
    df_estructuras_por_punto: pd.DataFrame,
    df_mat_por_punto: pd.DataFrame,
    datos_proyecto: dict
) -> bytes:
    buffer = BytesIO()
    doc = crear_doc(buffer)

    elems: list = []

    # 1) Hoja info
    elems = extend_flowables(elems, hoja_info_proyecto(datos_proyecto, df_estructuras, df_mat))
    safe_page_break(elems)

    # 2) Resumen de materiales (+ cables)
    elems.append(Paragraph("<b>Resumen de Materiales</b>", styles["Heading2"]))
    elems.append(Spacer(1, 8))

    df_agr = (
        df_mat.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
        if df_mat is not None and not df_mat.empty
        else pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])
    )

    if datos_proyecto.get("cables_proyecto"):
        for cable in datos_proyecto["cables_proyecto"]:
            tipo = cable.get("Tipo", "")
            calibre = cable.get("Calibre", "")
            longitud = cable.get("Total Cable (m)", cable.get("Longitud (m)", 0))
            if longitud and calibre:
                df_agr.loc[len(df_agr)] = [f"Cable {tipo} {calibre}", "m", float_safe(longitud, 0)]

    elems.append(tabla_resumen_materiales(df_agr))
    safe_page_break(elems)

    # 3) Materiales adicionales
    elems = agregar_tabla_materiales_adicionales(elems, datos_proyecto)

    # 4) Tabla de cables (tu módulo)
    elems = extend_flowables(elems, tabla_cables_pdf(datos_proyecto))

    # 5) Resumen de estructuras (con º intacto)
    if df_estructuras is not None and not df_estructuras.empty:
        safe_page_break(elems)
        elems.append(Paragraph("<b>Resumen de Estructuras</b>", styles["Heading2"]))
        elems.append(Spacer(1, 8))
        elems.append(tabla_resumen_estructuras(df_estructuras, doc.width))

    # 6) Estructuras por punto (con º intacto)
    if df_estructuras_por_punto is not None and not df_estructuras_por_punto.empty:
        safe_page_break(elems)
        elems.append(Paragraph("<b>Estructuras por Punto</b>", styles["Heading2"]))
        elems.append(Spacer(1, 8))

        puntos = sorted(df_estructuras_por_punto["Punto"].unique(),
                        key=lambda x: int(re.sub(r"\D", "", str(x)) or 0))

        for p in puntos:
            s = str(p).strip()
            m = re.search(r"(\d+)", s)
            num = str(int(m.group(1))) if m else s

            elems.append(Paragraph(f"<b>Punto {escape(str(num))}</b>", styles["Heading3"]))
            df_p = df_estructuras_por_punto[df_estructuras_por_punto["Punto"] == p]
            elems.append(tabla_estructuras_por_punto(df_p, doc.width))
            elems.append(Spacer(1, 0.2 * inch))

    # 7) Materiales por punto
    if df_mat_por_punto is not None and not df_mat_por_punto.empty:
        safe_page_break(elems)
        elems.append(Paragraph("<b>Materiales por Punto</b>", styles["Heading2"]))
        elems.append(Spacer(1, 8))

        puntos = sorted(df_mat_por_punto["Punto"].unique(),
                        key=lambda x: int(re.search(r"\d+", str(x)).group(0)) if re.search(r"\d+", str(x)) else 0)

        for p in puntos:
            s = str(p).strip()
            m = re.search(r"(\d+)", s)
            num = str(int(m.group(1))) if m else s

            elems.append(Paragraph(f"<b>Punto {escape(str(num))}</b>", styles["Heading3"]))
            df_p = df_mat_por_punto[df_mat_por_punto["Punto"] == p]
            df_agr_p = df_p.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
            elems.append(tabla_resumen_materiales(df_agr_p))
            elems.append(Spacer(1, 0.2 * inch))

    strip_trailing_pagebreaks(elems)
    doc.build(elems)

    out = buffer.getvalue()
    buffer.close()
    return out
