# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from datetime import datetime
from math import sqrt, floor
from typing import Dict, List, Optional, Tuple

import pandas as pd
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet


# ==========================================================
# HELPERS
# ==========================================================
def _float_safe(x, d=0.0):
    try:
        return float(x)
    except:
        return d


def _formato_tension(vll):
    try:
        vll = float(vll)
        vln = vll / sqrt(3)
        vln = floor(vln * 10) / 10
        return f"{vln:.1f} LN / {vll:.1f} LL KV"
    except:
        return str(vll)


def _col_cantidad(df):
    for c in ["Cantidad", "CANTIDAD", "cantidad"]:
        if c in df.columns:
            return c
    return None

def _normalizar_datos(d):
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
# 🔥 FIX CABLES
# ==========================================================
def _tipo_norm(c):
    t = str(c.get("Tipo", "")).upper().strip()

    if t in ["MT", "PRIMARIO"]:
        return "MT"
    if t in ["BT", "SECUNDARIO"]:
        return "BT"
    if t in ["N", "NEUTRO"]:
        return "N"
    if t in ["HP", "PILOTO"]:
        return "HP"
    if t in ["RET", "RETENIDA"]:
        return "RET"

    return t


# ==========================================================
# EXTRACTORES
# ==========================================================
def extraer_postes(df):
    if df is None or df.empty or "codigodeestructura" not in df.columns:
        return None, 0

    s = df["codigodeestructura"].astype(str)
    postes = df[s.str.contains(r"^(PC|PM|PT)-", case=False, na=False)]

    resumen = {}
    for _, r in postes.iterrows():
        cod = str(r["codigodeestructura"])
        cant = int(_float_safe(r.get("Cantidad", 0)))
        resumen[cod] = resumen.get(cod, 0) + cant

    return resumen, sum(resumen.values())


def extraer_transformadores(df):
    if df is None or df.empty:
        return 0

    s = df["codigodeestructura"].astype(str).str.upper()
    mask = s.str.contains(r"TS|TD|TT", na=False)

    total = 0
    for _, r in df[mask].iterrows():
        total += int(_float_safe(r.get("Cantidad", 0)))

    return total


def extraer_luminarias(df):
    if df is None or df.empty:
        return 0

    s = df["codigodeestructura"].astype(str).str.upper()
    mask = s.str.contains("LL", na=False)

    total = 0
    for _, r in df[mask].iterrows():
        total += int(_float_safe(r.get("Cantidad", 0)))

    return total


# ==========================================================
# TABLA
# ==========================================================
def build_tabla(datos, cables, tension_fmt, styleN, calibres_fn):

    cal_mt = calibres_fn(cables, "MT")
    cal_bt = calibres_fn(cables, "BT")
    cal_n = calibres_fn(cables, "N")
    cal_hp = calibres_fn(cables, "HP")

    data = [
        ["Nombre del Proyecto:", datos.get("nombre_proyecto", "")],
        ["Código / Expediente:", datos.get("codigo_proyecto", "")],
        ["Nivel de Tensión:", tension_fmt],
        ["Calibre Primario:", cal_mt],
        ["Calibre Secundario:", cal_bt],
        ["Calibre Neutro:", cal_n],
        ["Calibre Piloto:", cal_hp],
        ["Fecha de Informe:", datos.get("fecha_informe", datetime.today().strftime("%Y-%m-%d"))],
        ["Responsable:", datos.get("responsable", "")],
        ["Empresa:", datos.get("empresa", "")],
    ]

    t = Table(data, colWidths=[180, 300])
    t.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (0,-1), colors.lightgrey),
    ]))

    return [t, Spacer(1, 18)]


# ==========================================================
# DESCRIPCIÓN
# ==========================================================
def build_descripcion(datos, df_estructuras, cables, styleN):

    lineas = []

    resumen_postes, total_postes = extraer_postes(df_estructuras)
    if resumen_postes:
        partes = [f"{v} {k}" for k, v in resumen_postes.items()]
        lineas.append(f"Hincado de {', '.join(partes)} (Total: {total_postes} postes).")

    total_t = extraer_transformadores(df_estructuras)
    if total_t > 0:
        lineas.append(f"Instalación de {total_t} transformador(es).")

    total_l = extraer_luminarias(df_estructuras)
    if total_l > 0:
        lineas.append(f"Instalación de {total_l} luminarias.")

    primarios = [c for c in cables if _tipo_norm(c) == "MT"]
    bt = [c for c in cables if _tipo_norm(c) == "BT"]

    if primarios:
        total = sum(_float_safe(c.get("Longitud", 0)) for c in primarios)
        lineas.append(f"Construcción de {total:.0f} m de línea primaria.")

    if bt:
        total = sum(_float_safe(c.get("Longitud", 0)) for c in bt)
        lineas.append(f"Construcción de {total:.0f} m de línea secundaria.")

    texto = "<br/>".join([f"{i+1}. {l}" for i, l in enumerate(lineas)])

    return [
        Paragraph("<b>Descripción general del Proyecto:</b>", styleN),
        Spacer(1, 6),
        Paragraph(texto, styleN),
        Spacer(1, 18),
    ]


# ==========================================================
# FUNCIÓN PRINCIPAL (YA AUTÓNOMA)
# ==========================================================
def hoja_info_proyecto(
    datos_proyecto,
    df_estructuras=None,
    df_mat=None,
    *,
    styleN=None,
    styleH=None,
    _calibres_por_tipo=None,
):

    # 🔥 AUTOCONFIGURACIÓN
    if styleN is None or styleH is None:
        styles = getSampleStyleSheet()
        styleN = styles["Normal"]
        styleH = styles["Heading1"]

    if _calibres_por_tipo is None:
        def _calibres_por_tipo(cables, tipo):
            return ""

    tension = datos_proyecto.get("tension") or datos_proyecto.get("nivel_de_tension")
    tension_fmt = _formato_tension(tension)

    cables = datos_proyecto.get("cables_proyecto", []) or []

    elems = []

    elems.append(Paragraph("<b>Hoja de Información del Proyecto</b>", styleH))
    elems.append(Spacer(1, 12))

    elems.extend(build_tabla(datos_proyecto, cables, tension_fmt, styleN, _calibres_por_tipo))
    elems.extend(build_descripcion(datos_proyecto, df_estructuras, cables, styleN))

    return elems


# ==========================================================
# 🔷 WRAPPER LIMPIO
# ==========================================================
def seccion_hoja_info(
    datos_proyecto,
    df_estructuras=None,
    df_mat=None,
):
    return hoja_info_proyecto(
        datos_proyecto=datos_proyecto,
        df_estructuras=df_estructuras,
        df_mat=df_mat,
        styleN=None,
        styleH=None,
        _calibres_por_tipo=None,
    )
