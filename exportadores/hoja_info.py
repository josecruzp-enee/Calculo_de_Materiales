# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
import re
from exportadores.pdf_base import formatear_tension
# =========================================================
# HELPERS
# =========================================================
def _plural(palabra, n):
    return palabra if n == 1 else palabra + "es"


# =========================================================
# FORMATO TABLA (CATÁLOGO)
# =========================================================
def _formatear_calibre_catalogo(txt: str) -> str:
    txt = str(txt).strip()

    if not txt:
        return ""

    if "Cable de" in txt:
        return txt

    if "ACSR" in txt:
        return f"Cable de Aluminio {txt}"

    if "WP" in txt:
        return f"Cable de Aluminio Forrado {txt}"

    return txt


# =========================================================
# FORMATO TÉCNICO (DESCRIPCIÓN)
# =========================================================


def _formato_tecnico_calibre(txt: str):

    txt = str(txt).upper()

    # Detectar material
    if "ACSR" in txt:
        mat = "ACSR"
    elif "WP" in txt:
        mat = "WP"
    else:
        mat = ""

    # 🔥 EXTRAER CALIBRE CORRECTO
    match = re.search(r"#\s*([\d/]+)\s*AWG", txt)

    if match:
        calibre = match.group(1)
        return f"# {calibre} AWG {mat}".strip()

    # fallback (por si algo raro viene)
    return txt
# =========================================================
# CALIBRES TABLA
# =========================================================
def extraer_calibres(datos):

    prim = sec = neu = pil = ""
    cables = datos.get("cables_proyecto", [])

    for c in cables:
        tipo = str(c.get("Tipo", "")).upper()
        calibre = _formatear_calibre_catalogo(c.get("Calibre", ""))

        if tipo == "MT" and not prim:
            prim = calibre
        elif tipo == "BT" and not sec:
            sec = calibre
        elif tipo == "N" and not neu:
            neu = calibre
        elif tipo == "HP" and not pil:
            pil = calibre

    return prim, sec, neu, pil


# =========================================================
# DESCRIPCIÓN: POSTES
# =========================================================
def _desc_postes(df):

    postes = df[df["cod"].str.contains(r"^(PC|PCA|PM)-", regex=True, na=False)]
    if postes.empty:
        return None

    resumen = postes.groupby("cod")["Cantidad"].sum().reset_index()
    partes = [f'{int(r["Cantidad"])} {r["cod"]}' for _, r in resumen.iterrows()]
    total = int(postes["Cantidad"].sum())

    return f"Hincado de {', '.join(partes)} (Total: {total} postes)."


# =========================================================
# DESCRIPCIÓN: TRANSFORMADORES
# =========================================================
def _desc_transformadores(df):

    trafos = df[df["cod"].str.contains(r"\bT[ST]-", regex=True, na=False)]
    if trafos.empty:
        return None

    resumen = trafos.groupby("cod")["Cantidad"].sum().reset_index()
    partes = [f'{int(r["Cantidad"])} x {r["cod"]}' for _, r in resumen.iterrows()]
    total = int(trafos["Cantidad"].sum())

    tipo_txt = _plural("transformador", total)

    return f"Instalación de {total} {tipo_txt} en conexión {', '.join(partes)}."
    
# =========================================================
# DESCRIPCIÓN: LUMINARIAS
# =========================================================
def _desc_luminarias(df):

    lum = df[df["cod"].str.contains("LL")]
    if lum.empty:
        return None

    total = int(lum["Cantidad"].sum())

    potencias = []
    for cod in lum["cod"]:
        cod = str(cod).upper()
        if "W" in cod:
            try:
                potencias.append(cod.split("-")[-1])
            except:
                pass

    potencias = list(dict.fromkeys(potencias))

    if potencias:
        return f"Instalación de {total} luminarias tipo LED de {' / '.join(potencias)}."
    else:
        return f"Instalación de {total} luminarias tipo LED."


# =========================================================
# DESCRIPCIÓN: LÍNEAS
# =========================================================
from collections import defaultdict, Counter


def _desc_lineas(cables, tension):

    lineas = []

    # =========================
    # SEPARACIÓN
    # =========================
    mt = [c for c in cables if str(c.get("Tipo")).upper() == "MT"]
    bt = [c for c in cables if str(c.get("Tipo")).upper() == "BT"]
    neutro = [c for c in cables if str(c.get("Tipo")).upper() == "N"]
    piloto = [c for c in cables if str(c.get("Tipo")).upper() == "HP"]

    # =========================
    # NEUTRO (asumimos uno)
    # =========================
    n_calib = None
    if neutro:
        n_calib = _formato_tecnico_calibre(neutro[0].get("Calibre"))

    # =========================
    # MT → AGRUPAR POR FASES
    # =========================
    grupos_mt = defaultdict(list)

    for c in mt:
        fases = int(c.get("Conductores", 1))
        grupos_mt[fases].append(c)

    # 🔥 ORDEN CORRECTO: 3F → 2F → 1F
    for fases in sorted(grupos_mt.keys(), reverse=True):

        items = grupos_mt[fases]
        longitud = int(sum(float(i.get("Longitud", 0)) for i in items))

        conteo = Counter()
        for c in items:
            calib = _formato_tecnico_calibre(c.get("Calibre"))
            conteo[calib] += int(c.get("Conductores", 1))

        conductores = [f"{v} x {k}" for k, v in conteo.items()]

        if n_calib:
            conductores.append(f"1 x {n_calib}")

        desc = (
            f"Construcción de {longitud} m de LP, "
            f"{tension} kV, {fases}F+N, "
            + " + ".join(conductores)
        )

        lineas.append(desc)

    # =========================
    # BT (UN BLOQUE)
    # =========================
    longitud_bt = 0

    if bt:

        longitud_bt = int(sum(float(i.get("Longitud", 0)) for i in bt))
        fases = max(int(i.get("Conductores", 1)) for i in bt)

        conteo = Counter()
        for c in bt:
            calib = _formato_tecnico_calibre(c.get("Calibre"))
            conteo[calib] += int(c.get("Conductores", 1))

        conductores = [f"{v} x {k}" for k, v in conteo.items()]

        if n_calib:
            conductores.append(f"1 x {n_calib}")

        if piloto:
            p_calib = _formato_tecnico_calibre(piloto[0].get("Calibre"))
            conductores.append(f"1 x {p_calib}")

        config = f"{fases}F"
        if piloto:
            config += "+HP"
        config += "+N"

        desc = (
            f"Construcción de {longitud_bt} m de LS, "
            f"120/240 V, {config}, "
            + " + ".join(conductores)
        )

        lineas.append(desc)

    # =========================
    # HP INDEPENDIENTE (SI SOBRA)
    # =========================
    longitud_hp = int(sum(float(i.get("Longitud", 0)) for i in piloto))

    if longitud_hp > longitud_bt:

        diferencia = longitud_hp - longitud_bt

        if diferencia > 0:

            p_calib = _formato_tecnico_calibre(piloto[0].get("Calibre")) if piloto else ""

            conductores = []

            if p_calib:
                conductores.append(f"1 x {p_calib}")

            if n_calib:
                conductores.append(f"1 x {n_calib}")

            desc = (
                f"Construcción de {diferencia} m de HP, "
                f"120 V, 1F+N, "
                + " + ".join(conductores)
            )

            lineas.append(desc)

    return lineas

# =========================================================
# TABLA
# =========================================================
# =========================================================
# TABLA
# =========================================================
def _build_tabla(datos, prim, sec, neu, pil, doc_width):

    data = [
        ["Nombre del Proyecto:", datos.get("nombre_proyecto", "SIN NOMBRE")],
        ["Código / Expediente:", datos.get("codigo_proyecto", "N/A")],
        ["Nivel de Tensión (kV):", f"{formatear_tension(datos.get('tension'))} kV"],
        ["Calibre Primario:", prim or "N/A"],
        ["Calibre Secundario:", sec or "N/A"],
        ["Calibre Neutro:", neu or "N/A"],
        ["Calibre Piloto:", pil or "N/A"],
        ["Fecha de Informe:", datos.get("fecha_informe", "N/A")],
        ["Responsable:", datos.get("responsable", "N/A")],
        ["Empresa:", datos.get("empresa", "N/A")],
    ]

    # 🔥 ANCHO COMPLETO (clave)
    col1 = doc_width * 0.38
    col2 = doc_width * 0.62

    tabla = Table(data, colWidths=[col1, col2])

    tabla.setStyle(TableStyle([

        # GRID
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),

        # COLUMNA IZQUIERDA
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),

        # ALINEACIÓN
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        # 🔥 PADDING (esto mejora MUCHÍSIMO visual)
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),

    ]))

    return tabla


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================
def hoja_info_proyecto(datos_proyecto, df_estructuras=None, doc_width=None):

    styles = getSampleStyleSheet()
    styleN = styles["Normal"]

    # 🔥 TÍTULO CENTRADO
    styleTitulo = styles["Heading1"].clone("titulo_centrado")
    styleTitulo.alignment = TA_CENTER

    elems = []
    if doc_width is None:
        doc_width = 450

    elems.append(Paragraph("Hoja de Información del Proyecto", styleTitulo))
    elems.append(Spacer(1, 8))

    datos = datos_proyecto or {}
    cables = datos.get("cables_proyecto", [])

    prim, sec, neu, pil = extraer_calibres(datos)

    elems.append(_build_tabla(datos, prim, sec, neu, pil, doc_width))
    elems.append(Spacer(1, 8))

    elems.append(Paragraph("<b>Descripción general del Proyecto:</b>", styleN))
    elems.append(Spacer(1, 6))

    lineas = []

    if isinstance(df_estructuras, pd.DataFrame) and not df_estructuras.empty:
        df = df_estructuras.copy()
        df["cod"] = df["Estructura"].astype(str).str.upper()

        for fn in [_desc_postes, _desc_transformadores, _desc_luminarias]:
            res = fn(df)
            if res:
                lineas.append(res)

    tension = formatear_tension(datos.get("tension"))
    lineas.extend(_desc_lineas(cables, tension))

    if not lineas:
        lineas.append("No se cuenta con información suficiente.")

    for i, l in enumerate(lineas):
        elems.append(Paragraph(f"{i+1}. {l}", styleN))
        elems.append(Spacer(1, 4))

    elems.append(Spacer(1, 10))

    return elems


# =========================================================
# WRAPPER
# =========================================================
def seccion_hoja_info(datos_proyecto, df_estructuras, df_mat, doc_width=None):
    return hoja_info_proyecto(
        datos_proyecto=datos_proyecto,
        df_estructuras=df_estructuras,
        doc_width=doc_width
    )

# =========================================================
# PDF INDEPENDIENTE
# =========================================================
from io import BytesIO

from reportlab.platypus import (
    BaseDocTemplate,
    PageTemplate,
    Frame
)

from reportlab.lib.pagesizes import letter

from exportadores.pdf_base import fondo_pagina


def generar_pdf_hoja_info(
    datos_proyecto,
    df_estructuras
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

    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height
    )

    template = PageTemplate(
        id="normal",
        frames=[frame],
        onPage=fondo_pagina
    )

    doc.addPageTemplates([template])

    elems = hoja_info_proyecto(
        datos_proyecto=datos_proyecto,
        df_estructuras=df_estructuras,
        doc_width=doc.width
    )

    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
