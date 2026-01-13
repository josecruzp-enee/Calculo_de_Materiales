# -*- coding: utf-8 -*-
"""
pdf_utils.py
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
def safe_page_break(elems):
    if elems and not isinstance(elems[-1], PageBreak):
        elems.append(PageBreak())


def extend_flowables(elems, extra):
    if not extra:
        return elems
    if elems and isinstance(elems[-1], PageBreak) and isinstance(extra[0], PageBreak):
        extra = extra[1:]
    elems.extend(extra)
    return elems


def strip_trailing_pagebreaks(elems):
    while elems and isinstance(elems[-1], PageBreak):
        elems.pop()
    return elems


# ==========================
# FONDO DE PÁGINA
# ==========================
def fondo_pagina(canvas, doc):
    try:
        canvas.saveState()
        fondo = os.path.join(BASE_DIR, "data", "Imagen Encabezado.jpg")
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
# HOJA INFO PROYECTO
# ==========================================================
def hoja_info_proyecto(datos_proyecto, df_estructuras=None, df_mat=None):
    from math import sqrt, floor

    def float_safe(x, d=0.0):
        try:
            return float(x)
        except Exception:
            return d

    def formato_tension(vll):
        """
        Ej: 13.8 -> '7.9 LN / 13.8 LL KV' (LN truncado a 1 decimal).
        """
        try:
            vll = float(vll)
            vln = vll / sqrt(3)
            vln = floor(vln * 10) / 10  # truncar 1 decimal
            return f"{vln:.1f} LN / {vll:.1f} LL KV"
        except Exception:
            return str(vll)

    elems = []
    elems.append(Paragraph("<b>Hoja de Información del Proyecto</b>", styleH))
    elems.append(Spacer(1, 12))

    # ==== DATOS DEL PROYECTO ====
    descripcion_manual = (datos_proyecto.get("descripcion_proyecto", "") or "").strip()
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
        if "codigodeestructura" in df_estructuras.columns:
            postes = df_estructuras[
                df_estructuras["codigodeestructura"].astype(str).str.contains("PC|PT", case=False, na=False)
            ]
        else:
            postes = pd.DataFrame()

        if not postes.empty:
            resumen = {}
            for _, r in postes.iterrows():
                cod = r["codigodeestructura"]
                cant = int(float_safe(r.get("Cantidad", 0), 0))
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
    total_t = 0
    capacidades = []
    mult = {"TS": 1, "TD": 2, "TT": 3}

    # 1) Buscar en ESTRUCTURAS (codigodeestructura)
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

    # 2) Fallback: buscar en MATERIALES (Materiales)
    if total_t == 0 and df_mat is not None and not df_mat.empty and "Materiales" in df_mat.columns:
        s = df_mat["Materiales"].astype(str).str.upper().str.strip()
        ext = s.str.extract(r"\b(TS|TD|TT)\s*-\s*(\d+(?:\.\d+)?)\s*KVA\b", expand=True)
        mask = ext[0].notna()

        if mask.any():
            df_tx = df_mat.loc[mask].copy()
            if "Cantidad" in df_tx.columns:
                df_tx["Cantidad"] = pd.to_numeric(df_tx["Cantidad"], errors="coerce").fillna(0)
            else:
                df_tx["Cantidad"] = 0

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

    # --- Luminarias (CORREGIDO para que no truene) ---
    # Requisitos mínimos: df_mat no vacío y que exista la columna Materiales
    if df_mat is not None and not df_mat.empty and "Materiales" in df_mat.columns:
        # Cantidad puede venir como 'Cantidad' o 'CANTIDAD' según tu pipeline, tratamos ambos.
        col_cant = "Cantidad" if "Cantidad" in df_mat.columns else ("CANTIDAD" if "CANTIDAD" in df_mat.columns else None)

        lums = df_mat[
            df_mat["Materiales"].astype(str).str.contains(r"Lámpara|Lampara|Alumbrado", case=False, na=False)
        ].copy()

        if not lums.empty:
            if col_cant:
                lums[col_cant] = pd.to_numeric(lums[col_cant], errors="coerce").fillna(0)
            else:
                # si no hay cantidad, no podemos sumar -> 0
                lums["Cantidad"] = 0
                col_cant = "Cantidad"

            def pot(txt):
                s = str(txt).upper().replace("–", "-")

                # Caso 28A50W (ej: LL-1-28A50W)
                m = re.search(r"(\d+)\s*A\s*(\d+)\s*W", s)
                if m:
                    return f"{m.group(1)}-{m.group(2)} W"

                # Caso 28-50W
                m = re.search(r"(\d+)\s*-\s*(\d+)\s*W", s)
                if m:
                    return f"{m.group(1)}-{m.group(2)} W"

                # Caso 100W
                m = re.search(r"(\d+)\s*W", s)
                if m:
                    return f"{m.group(1)} W"

                return "SIN POTENCIA"

            resumen = (
                lums.assign(Pot=lums["Materiales"].map(pot))
                    .groupby("Pot")[col_cant]
                    .sum()
                    .round()
                    .astype(int)
                    .sort_index()
            )

            total = int(resumen.sum())
            det = " y ".join([f"{v} de {k}" for k, v in resumen.items()])
            lineas.append(f"Instalación de {total} luminaria(s) de alumbrado público ({det}).")

    # ==== Párrafo final ====
    descripcion_auto = "<br/>".join([f"{i + 1}. {l}" for i, l in enumerate(lineas)])
    cuerpo_desc = (descripcion_manual + "<br/><br/>" + descripcion_auto) if descripcion_manual else descripcion_auto

    elems.append(Paragraph("<b>Descripción general del Proyecto:</b>", styleN))
    elems.append(Spacer(1, 6))
    elems.append(Paragraph(cuerpo_desc, styleN))
    elems.append(Spacer(1, 18))

    return elems

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
# PDF COMPLETO (EL PRINCIPAL)
# ==========================================================
def generar_pdf_completo(
    df_mat,
    df_estructuras,
    df_estructuras_por_punto,
    df_mat_por_punto,
    datos_proyecto
):
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = []

    # --- Hoja de información ---
    elems = extend_flowables(elems, hoja_info_proyecto(datos_proyecto, df_estructuras, df_mat))

    # --- Resumen de materiales ---
    safe_page_break(elems)
    elems.append(Paragraph("<b>Resumen de Materiales</b>", styles["Heading2"]))

    if df_mat is not None and not df_mat.empty:
        df_agr = df_mat.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
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
        ]))
        elems.append(tabla)

    # --- Tabla de cables ---
    elems = extend_flowables(elems, tabla_cables_pdf(datos_proyecto))

    # --- Estructuras ---
    if df_estructuras is not None and not df_estructuras.empty:
        safe_page_break(elems)
        elems.append(Paragraph("<b>Resumen de Estructuras</b>", styles["Heading2"]))
        tabla = _tabla_estructuras_por_punto("GLOBAL", df_estructuras, doc.width)
        elems.append(tabla)

    # --- Estructuras por punto ---
    if df_estructuras_por_punto is not None and not df_estructuras_por_punto.empty:
        safe_page_break(elems)
        elems.append(Paragraph("<b>Estructuras por Punto</b>", styles["Heading2"]))

        puntos = sorted(
            df_estructuras_por_punto["Punto"].unique(),
            key=lambda x: int(re.sub(r"\D", "", str(x)) or 0)
        )

        for p in puntos:
            m = re.search(r"(\d+)", str(p))
            num = m.group(1) if m else str(p)

            elems.append(Paragraph(f"<b>Punto {escape(num)}</b>", styles["Heading3"]))
            df_p = df_estructuras_por_punto[df_estructuras_por_punto["Punto"] == p]
            elems.append(_tabla_estructuras_por_punto(num, df_p, doc.width))
            elems.append(Spacer(1, 0.2 * inch))

    strip_trailing_pagebreaks(elems)
    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

