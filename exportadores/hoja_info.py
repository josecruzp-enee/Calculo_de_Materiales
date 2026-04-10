# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from math import sqrt, floor
from typing import List
import pandas as pd

from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet


# ==========================================================
# NORMALIZADOR
# ==========================================================
def _normalizar_datos(d: dict) -> dict:
    return {
        "nombre_proyecto": d.get("nombre_proyecto") or d.get("nombre", "SIN NOMBRE"),
        "codigo_proyecto": d.get("codigo_proyecto") or d.get("codigo", "N/A"),
        "empresa": d.get("empresa", "N/A"),
        "tension": d.get("tension") or d.get("nivel_de_tension"),
        "fecha_informe": d.get("fecha_informe") or datetime.today().strftime("%Y-%m-%d"),
        "responsable": d.get("responsable", "N/A"),
        "cables_proyecto": d.get("cables_proyecto", []),
    }


# ==========================================================
# FORMATO TENSIÓN
# ==========================================================
def _formato_tension(vll):
    try:
        vll = float(vll)
        vln = vll / sqrt(3)
        vln = floor(vln * 10) / 10
        return f"{vln:.1f} / {vll:.1f} kV"
    except:
        return str(vll)


# ==========================================================
# CALIBRES AUTOMÁTICOS (SIMPLIFICADO PERO ÚTIL)
# ==========================================================
def _extraer_calibres(cables, tipo):
    for c in cables:
        if str(c.get("Tipo", "")).upper() == tipo:
            return c.get("Materiales") or c.get("Calibre") or ""
    return ""


# ==========================================================
# TABLA PRINCIPAL
# ==========================================================
def build_tabla(datos, cables, tension_fmt, styleN):

    calibre_primario = _extraer_calibres(cables, "MT")
    calibre_secundario = _extraer_calibres(cables, "BT")
    calibre_neutro = _extraer_calibres(cables, "N")
    calibre_piloto = _extraer_calibres(cables, "HP")

    data = [
        ["Nombre del Proyecto:", datos["nombre_proyecto"]],
        ["Código / Expediente:", datos["codigo_proyecto"]],
        ["Nivel de Tensión (kV):", tension_fmt],
        ["Calibre Primario:", calibre_primario],
        ["Calibre Secundario:", calibre_secundario],
        ["Calibre Neutro:", calibre_neutro],
        ["Calibre Piloto:", calibre_piloto],
        ["Fecha de Informe:", datos["fecha_informe"]],
        ["Responsable:", datos["responsable"]],
        ["Empresa:", datos["empresa"]],
    ]

    tabla = Table(data, colWidths=[200, 340])

    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#D9D9D9")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    return [tabla, Spacer(1, 15)]


# ==========================================================
# DESCRIPCIÓN INTELIGENTE
# ==========================================================
def build_descripcion(df_estructuras, styleN):

    lineas = []

    if df_estructuras is not None and not df_estructuras.empty:

        # POSTES
        postes = df_estructuras[df_estructuras["codigodeestructura"].str.contains("PC", na=False)]
        if not postes.empty:
            total = int(postes["Cantidad"].sum())
            lineas.append(f"Hincado de {total} postes.")

        # TRANSFORMADORES
        trafos = df_estructuras[df_estructuras["codigodeestructura"].str.contains("TS", na=False)]
        if not trafos.empty:
            total = int(trafos["Cantidad"].sum())
            lineas.append(f"Instalación de {total} transformador(es).")

        # LUMINARIAS
        lum = df_estructuras[df_estructuras["codigodeestructura"].str.contains("LL", na=False)]
        if not lum.empty:
            total = int(lum["Cantidad"].sum())
            lineas.append(f"Instalación de {total} luminarias.")

    if not lineas:
        lineas.append("No se cuenta con información suficiente.")

    texto = "<br/>".join([f"{i+1}. {l}" for i, l in enumerate(lineas)])

    return [
        Paragraph("<b>Descripción general del Proyecto:</b>", styleN),
        Spacer(1, 6),
        Paragraph(texto, styleN),
        Spacer(1, 12),
    ]


# ==========================================================
# FUNCIÓN PRINCIPAL
# ==========================================================
def hoja_info_proyecto(
    datos_proyecto,
    df_estructuras=None,
    df_mat=None,
):

    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    styleH = styles["Heading1"]

    datos = _normalizar_datos(datos_proyecto)

    # 🔥 INYECTAR CABLES
    if df_mat is not None and not df_mat.empty:
        datos["cables_proyecto"] = df_mat.to_dict(orient="records")

    tension_fmt = _formato_tension(datos["tension"])
    cables = datos["cables_proyecto"]

    elems = []

    elems.append(Paragraph("Hoja de Información del Proyecto", styleH))
    elems.append(Spacer(1, 12))

    elems.extend(build_tabla(datos, cables, tension_fmt, styleN))
    elems.extend(build_descripcion(df_estructuras, styleN))

    return elems


# ==========================================================
# WRAPPER
# ==========================================================
def seccion_hoja_info(
    datos_proyecto,
    df_estructuras=None,
    df_mat=None,
):
    return hoja_info_proyecto(
        datos_proyecto,
        df_estructuras,
        df_mat,
    )
