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

# --- Importación de tabla de cables ---
from modulo.configuracion_cables import tabla_cables_pdf


# ==========================================================
# ESTILOS COMUNES
# ==========================================================
styles = getSampleStyleSheet()
styleN = ParagraphStyle(name="Normal9", parent=styles["Normal"], fontSize=9, leading=11)
styleH = styles["Heading1"]

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# ==========================================================
# HELPERS FLOWABLES (ANTI PÁGINAS EN BLANCO)
# ==========================================================
def safe_page_break(elems: list) -> None:
    """Agrega PageBreak solo si el último elemento NO es PageBreak."""
    if elems and not isinstance(elems[-1], PageBreak):
        elems.append(PageBreak())


def extend_flowables(elems: list, extra: list) -> list:
    """Extiende evitando doble PageBreak entre listas."""
    if not extra:
        return elems
    if elems and isinstance(elems[-1], PageBreak) and isinstance(extra[0], PageBreak):
        extra = extra[1:]
    elems.extend(extra)
    return elems


def strip_trailing_pagebreaks(elems: list) -> list:
    """Elimina PageBreak al final (evita página en blanco final)."""
    while elems and isinstance(elems[-1], PageBreak):
        elems.pop()
    return elems


# ==========================================================
# HELPERS GENERALES
# ==========================================================
def crear_doc(buffer: BytesIO, on_page=None) -> BaseDocTemplate:
    """Crea el documento con un template con fondo."""
    doc = BaseDocTemplate(buffer, pagesize=letter)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="fondo", frames=[frame], onPage=on_page or fondo_pagina)
    doc.addPageTemplates([template])
    return doc


def float_safe(x, d: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return d


def _safe_para(texto: object) -> str:
    """Texto seguro para Paragraph + cortes suaves para tokens largos."""
    t = normalizar_texto_pdf(texto)
    t = escape(t)
    t = t.replace("-", "-\u200b").replace("/", "/\u200b").replace("_", "_\u200b")
    return t



# ==========================================================
# ✅ FIX: formatear_material (IDENTIDAD)
# ==========================================================
def formatear_material(nombre) -> str:
    """
    Ya NO formatea (porque tu catálogo base ya está normalizado).
    Solo convierte a texto seguro para Paragraph.
    """
    if nombre is None or (isinstance(nombre, float) and pd.isna(nombre)):
        return ""
    return escape(str(nombre).strip())


# ==========================================================
# FONDO PARA TODAS LAS PÁGINAS
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


# ==========================================================
# ✅ Calibres desde tabla de Cables (sin longitudes)
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


def _formato_tension(vll) -> str:
    """Ej: 13.8 -> '7.9 LN / 13.8 LL KV' (LN truncado a 1 decimal)."""
    from math import sqrt, floor

    try:
        vll = float(vll)
        vln = vll / sqrt(3)
        vln = floor(vln * 10) / 10  # truncar (no redondear)
        return f"{vln:.1f} LN / {vll:.1f} LL KV"
    except Exception:
        return str(vll)


# ==========================================================
# SECCIÓN: DESCRIPCIÓN GENERAL (modular)
# ==========================================================
def _desc_postes(df_estructuras: pd.DataFrame) -> list[str]:
    lineas = []
    if df_estructuras is None or df_estructuras.empty or "codigodeestructura" not in df_estructuras.columns:
        return lineas

    postes = df_estructuras[
        df_estructuras["codigodeestructura"].astype(str).str.contains("PC|PT", case=False, na=False)
    ]
    if postes.empty:
        return lineas

    resumen = {}
    for _, r in postes.iterrows():
        cod = str(r.get("codigodeestructura", "")).strip()
        cant = int(float_safe(r.get("Cantidad", 0), 0))
        if cod:
            resumen[cod] = resumen.get(cod, 0) + cant

    partes = [f"{v} {k}" for k, v in resumen.items()]
    total = sum(resumen.values())
    lineas.append(f"Hincado de {', '.join(partes)} (Total: {total} postes).")
    return lineas


def _desc_lineas_primarias(primarios: list[dict], nivel_tension_fmt: str) -> list[str]:
    lineas = []
    for c in primarios or []:
        long_total = float_safe(c.get("Total Cable (m)", c.get("Longitud (m)", 0)))
        fase = str(c.get("Configuración", "")).strip().upper()
        calibre = str(c.get("Calibre", "")).strip()

        m = re.search(r"(\d+)\s*F", fase)
        n_fases = int(m.group(1)) if m else 1
        long_desc = (long_total / n_fases) if n_fases > 1 else long_total

        if long_desc > 0 and calibre:
            lineas.append(f"Construcción de {long_desc:.0f} m de LP, {nivel_tension_fmt}, {fase}, {calibre}.")
    return lineas


def _desc_lineas_secundarias(secundarios: list[dict]) -> list[str]:
    lineas = []
    for c in secundarios or []:
        long_total = float_safe(c.get("Total Cable (m)", 0))
        fase = str(c.get("Configuración", "")).strip().upper()
        calibre = str(c.get("Calibre", "")).strip()

        m = re.search(r"(\d+)\s*F", fase)
        n_fases = int(m.group(1)) if m else 1
        long_desc = (long_total / n_fases) if n_fases > 1 else long_total

        if long_desc > 0 and calibre:
            lineas.append(f"Construcción de {long_desc:.0f} m de LS, 120/240 V, {fase}, {calibre}.")
    return lineas


def _desc_transformadores(df_estructuras: pd.DataFrame, df_mat: pd.DataFrame) -> list[str]:
    lineas = []
    total_t = 0
    capacidades = []
    mult = {"TS": 1, "TD": 2, "TT": 3}

    # 1) Buscar en ESTRUCTURAS
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

    # 2) Fallback: buscar en MATERIALES
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
    return lineas


def _desc_luminarias(df_mat: pd.DataFrame) -> list[str]:
    lineas = []
    if df_mat is None or df_mat.empty or "Materiales" not in df_mat.columns:
        return lineas

    # 1) Primero intentar SOLO luminarias tipo LL-
    lums = df_mat[
        df_mat["Materiales"].astype(str).str.contains(r"\bLL-\s*\d", case=False, na=False)
    ].copy()

    # 2) Si no hay LL-, entonces fallback al filtro general
    if lums.empty:
        lums = df_mat[
            df_mat["Materiales"].astype(str).str.contains("Lámpara|Lampara|Alumbrado", case=False, na=False)
        ].copy()

    if lums.empty:
        return lineas

    lums["Cantidad"] = pd.to_numeric(lums.get("Cantidad", 0), errors="coerce").fillna(0)

    def pot(txt):
        s = normalizar_texto_pdf(txt).upper()

        # LL-1-28A50 W  (o 28A50W)
        m = re.search(r"(\d+)\s*A\s*(\d+)\s*W", s)
        if m:
            return f"{m.group(1)}-{m.group(2)} W"

        # 28-50 W
        m = re.search(r"(\d+)\s*-\s*(\d+)\s*W", s)
        if m:
            return f"{m.group(1)}-{m.group(2)} W"

        # 100 W
        m = re.search(r"(\d+)\s*W", s)
        if m:
            return f"{m.group(1)} W"

        return "SIN POTENCIA"

    resumen = (
        lums.assign(Pot=lums["Materiales"].map(pot))
            .groupby("Pot")["Cantidad"].sum()
            .round().astype(int)
    )

    total = int(resumen.sum())

    # Orden más natural (28-50 primero, 100 después)
    def _k(x):
        m = re.search(r"(\d+)", str(x))
        return int(m.group(1)) if m else 999999

    items = sorted(resumen.items(), key=lambda kv: _k(kv[0]))
    det = " y ".join([f"{v} de {k}" for k, v in items])

    lineas.append(f"Instalación de {total} luminaria(s) de alumbrado público ({det}).")
    return lineas



def construir_descripcion_general(
    descripcion_manual: str,
    df_estructuras: pd.DataFrame,
    df_mat: pd.DataFrame,
    primarios: list[dict],
    secundarios: list[dict],
    nivel_tension_fmt: str,
) -> str:
    lineas = []
    lineas += _desc_postes(df_estructuras)
    lineas += _desc_lineas_primarias(primarios, nivel_tension_fmt)
    lineas += _desc_lineas_secundarias(secundarios)
    lineas += _desc_transformadores(df_estructuras, df_mat)
    lineas += _desc_luminarias(df_mat)

    descripcion_auto = "<br/>".join([f"{i + 1}. {l}" for i, l in enumerate(lineas)])
    return (descripcion_manual + "<br/><br/>" + descripcion_auto) if descripcion_manual else descripcion_auto


# ==========================================================
# SECCIÓN: HOJA INFO PROYECTO
# ==========================================================
def hoja_info_proyecto(datos_proyecto: dict, df_estructuras=None, df_mat=None) -> list:
    from math import sqrt

    elems = []
    elems.append(Paragraph("<b>Hoja de Información del Proyecto</b>", styleH))
    elems.append(Spacer(1, 12))

    # ==== DATOS DEL PROYECTO ====
    descripcion_manual = str(datos_proyecto.get("descripcion_proyecto", "") or "").strip()
    tension_valor = datos_proyecto.get("nivel_de_tension") or datos_proyecto.get("tension") or ""
    nivel_tension_fmt = _formato_tension(tension_valor)

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

    # ==== DESCRIPCIÓN GENERAL (auto) ====
    cuerpo_desc = construir_descripcion_general(
        descripcion_manual=descripcion_manual,
        df_estructuras=df_estructuras,
        df_mat=df_mat,
        primarios=primarios,
        secundarios=secundarios,
        nivel_tension_fmt=nivel_tension_fmt,
    )

    elems.append(Paragraph("<b>Descripción general del Proyecto:</b>", styleN))
    elems.append(Spacer(1, 6))
    elems.append(Paragraph(cuerpo_desc, styleN))
    elems.append(Spacer(1, 18))

    return elems


# ==========================================================
# SECCIÓN: TABLA RESUMEN MATERIALES (helper)
# ==========================================================
def _tabla_resumen_materiales(df_mat_agr: pd.DataFrame) -> Table:
    data = [["Material", "Unidad", "Cantidad"]]
    for _, r in df_mat_agr.iterrows():
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
    return tabla


# ==========================================================
# SECCIÓN: TABLA RESUMEN ESTRUCTURAS (robusta)
# ==========================================================
def _seccion_resumen_estructuras(df_estructuras: pd.DataFrame, doc_width: float) -> list:
    elems = []

    st_hdr = ParagraphStyle(
        "hdr_est2", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=9, leading=10, alignment=TA_CENTER
    )
    st_code = ParagraphStyle(
        "code_est2", parent=styles["Normal"], fontName="Helvetica",
        fontSize=8, leading=9, alignment=TA_LEFT
    )
    st_desc = ParagraphStyle(
        "desc_est2", parent=styles["Normal"], fontName="Helvetica",
        fontSize=8, leading=9, alignment=TA_LEFT, wordWrap="CJK"
    )
    st_desc.splitLongWords = 1
    st_desc.spaceShrinkage = 0.05

    st_qty = ParagraphStyle(
        "qty_est2", parent=styles["Normal"], fontName="Helvetica",
        fontSize=8, leading=9, alignment=TA_CENTER
    )

    ancho_util = doc_width * 0.98
    w1, w2, w3 = ancho_util * 0.18, ancho_util * 0.67, ancho_util * 0.15

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

    tabla = Table(data, colWidths=[w1, w2, w3], repeatRows=1, hAlign="CENTER")
    tabla.setStyle(TableStyle([
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

    elems.append(tabla)
    return elems


# ==========================================================
# SECCIÓN: ESTRUCTURAS POR PUNTO (tabla helper)
# ==========================================================
def _tabla_estructuras_por_punto(punto: str, df_p: pd.DataFrame, doc_width: float) -> Table:
    st_hdr = ParagraphStyle(
        "hdr_p", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=9, leading=10, alignment=TA_CENTER
    )
    st_code = ParagraphStyle(
        "code_p", parent=styles["Normal"], fontName="Helvetica",
        fontSize=8, leading=9, alignment=TA_LEFT
    )
    st_desc = ParagraphStyle(
        "desc_p", parent=styles["Normal"], fontName="Helvetica",
        fontSize=8, leading=9, alignment=TA_LEFT, wordWrap="CJK"
    )
    st_desc.splitLongWords = 1

    st_qty = ParagraphStyle(
        "qty_p", parent=styles["Normal"], fontName="Helvetica",
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
            Paragraph(_safe_para(row.get("codigodeestructura", "")), st_code),
            Paragraph(_safe_para(row.get("Descripcion", "")), st_desc),
            Paragraph(_safe_para(row.get("Cantidad", "")), st_qty),
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
# MATERIALS ADICIONALES (sección)
# ==========================================================
def agregar_tabla_materiales_adicionales(elems: list, datos_proyecto: dict) -> list:
    df_extra = datos_proyecto.get("materiales_extra")
    if df_extra is None or df_extra.empty:
        return elems

    safe_page_break(elems)
    elems.append(Paragraph("<b>Materiales Adicionales</b>", styles["Heading2"]))
    elems.append(Spacer(1, 12))

    st_mat = ParagraphStyle(
        "mat_wrap",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=9,
        alignment=TA_LEFT,
        wordWrap="CJK",
    )
    st_mat.splitLongWords = 1

    st_mid = ParagraphStyle(
        "mid",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=9,
        alignment=TA_CENTER,
    )

    data_extra = [[
        Paragraph("<b>Material</b>", st_mid),
        Paragraph("<b>Unidad</b>", st_mid),
        Paragraph("<b>Cantidad</b>", st_mid),
    ]]

    for _, row in df_extra.iterrows():
        mat = escape(str(row.get("Materiales", "")).strip())
        uni = escape(str(row.get("Unidad", "")).strip())
        cant = float_safe(row.get("Cantidad", 0) or 0)

        data_extra.append([
            Paragraph(mat, st_mat),
            Paragraph(uni, st_mid),
            Paragraph(f"{cant:.2f}", st_mid),
        ])

    tabla = Table(data_extra, colWidths=[4 * inch, 1 * inch, 1 * inch])
    tabla.setStyle(TableStyle([
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

    elems.append(tabla)
    return elems


# ==========================================================
# PDFs INDIVIDUALES (materiales / estructuras / por punto)
# ==========================================================
def generar_pdf_materiales(df_mat: pd.DataFrame, nombre_proy: str, datos_proyecto: dict | None = None) -> bytes:
    buffer = BytesIO()
    doc = crear_doc(buffer, on_page=fondo_pagina)

    elems = [
        Paragraph(f"<b>Resumen de Materiales - Proyecto: {escape(str(nombre_proy))}</b>", styles["Title"]),
        Spacer(1, 12)
    ]

    df_agrupado = df_mat.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
    elems.append(_tabla_resumen_materiales(df_agrupado))

    doc.build(elems)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def generar_pdf_estructuras_global(df_estructuras: pd.DataFrame, nombre_proy: str) -> bytes:
    buffer = BytesIO()
    doc = crear_doc(buffer, on_page=fondo_pagina)

    elems = [
        Paragraph(f"<b>Resumen de Estructuras - Proyecto: {escape(str(nombre_proy))}</b>", styles["Title"]),
        Spacer(1, 10),
    ]

    elems.extend(_seccion_resumen_estructuras(df_estructuras, doc.width))

    doc.build(elems)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def generar_pdf_estructuras_por_punto(df_por_punto: pd.DataFrame, nombre_proy: str) -> bytes:
    buffer = BytesIO()
    doc = crear_doc(buffer, on_page=fondo_pagina)

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
        tabla_p = _tabla_estructuras_por_punto(str(num), df_p, doc.width)
        elems.append(tabla_p)
        elems.append(Spacer(1, 0.2 * inch))

    doc.build(elems)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def generar_pdf_materiales_por_punto(df_por_punto: pd.DataFrame, nombre_proy: str) -> bytes:
    buffer = BytesIO()
    doc = crear_doc(buffer, on_page=fondo_pagina)

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
        df_agrupado = df_p.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

        elems.append(_tabla_resumen_materiales(df_agrupado))
        elems.append(Spacer(1, 0.2 * inch))

    doc.build(elems)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ==========================================================
# PDF COMPLETO (ORQUESTADOR)
# ==========================================================
def generar_pdf_completo(
    df_mat: pd.DataFrame,
    df_estructuras: pd.DataFrame,
    df_estructuras_por_punto: pd.DataFrame,
    df_mat_por_punto: pd.DataFrame,
    datos_proyecto: dict
) -> bytes:
    buffer = BytesIO()
    doc = crear_doc(buffer, on_page=fondo_pagina)

    elems: list = []

    # 1) Hoja de info + descripción general
    elems = extend_flowables(elems, hoja_info_proyecto(datos_proyecto, df_estructuras, df_mat))
    safe_page_break(elems)

    # 2) Resumen de materiales
    elems.append(Paragraph("<b>Resumen de Materiales</b>", styles["Heading2"]))
    elems.append(Spacer(1, 8))

    df_agr = (
        df_mat.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
        if df_mat is not None and not df_mat.empty
        else pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])
    )

    # Agregar cables del proyecto al resumen
    if datos_proyecto.get("cables_proyecto"):
        for cable in datos_proyecto["cables_proyecto"]:
            tipo = cable.get("Tipo", "")
            calibre = cable.get("Calibre", "")
            longitud = cable.get("Total Cable (m)", cable.get("Longitud (m)", 0))
            if longitud and calibre:
                descripcion = f"Cable {tipo} {calibre}"
                df_agr.loc[len(df_agr)] = [descripcion, "m", float_safe(longitud, 0)]

    elems.append(_tabla_resumen_materiales(df_agr))
    safe_page_break(elems)

    # 3) Materiales adicionales
    elems = agregar_tabla_materiales_adicionales(elems, datos_proyecto)

    # 4) Tabla de cables (tu módulo)
    elems = extend_flowables(elems, tabla_cables_pdf(datos_proyecto))

    # 5) Resumen de estructuras
    if df_estructuras is not None and not df_estructuras.empty:
        safe_page_break(elems)
        elems.append(Paragraph("<b>Resumen de Estructuras</b>", styles["Heading2"]))
        elems.append(Spacer(1, 8))
        elems.extend(_seccion_resumen_estructuras(df_estructuras, doc.width))

    # 6) Estructuras por punto
    if df_estructuras_por_punto is not None and not df_estructuras_por_punto.empty:
        safe_page_break(elems)
        elems.append(Paragraph("<b>Estructuras por Punto</b>", styles["Heading2"]))
        elems.append(Spacer(1, 8))

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
            elems.append(_tabla_estructuras_por_punto(num, df_p, doc.width))
            elems.append(Spacer(1, 0.2 * inch))

    # 7) Materiales por punto
    if df_mat_por_punto is not None and not df_mat_por_punto.empty:
        safe_page_break(elems)
        elems.append(Paragraph("<b>Materiales por Punto</b>", styles["Heading2"]))
        elems.append(Spacer(1, 8))

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

            elems.append(_tabla_resumen_materiales(df_agr_p))
            elems.append(Spacer(1, 0.2 * inch))

    strip_trailing_pagebreaks(elems)

    doc.build(elems)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

