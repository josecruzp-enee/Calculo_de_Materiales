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
# 🔷 NORMALIZADOR (CLAVE)
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
        return ""


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

    return int(df[mask]["Cantidad"].sum()) if "Cantidad" in df.columns else 0


def extraer_luminarias(df):
    if df is None or df.empty:
        return 0

    s = df["codigodeestructura"].astype(str).str.upper()
    mask = s.str.contains("LL", na=False)

    return int(df[mask]["Cantidad"].sum()) if "Cantidad" in df.columns else 0


# ==========================================================
# TABLA
# ==========================================================
def build_tabla(datos, cables, tension_fmt, styleN):

    data = [
        ["Nombre del Proyecto:", datos["nombre_proyecto"]],
        ["Código / Expediente:", datos["codigo_proyecto"]],
        ["Nivel de Tensión:", tension_fmt],
        ["Fecha de Informe:", datos["fecha_informe"]],
        ["Responsable:", datos["responsable"]],
        ["Empresa:", datos["empresa"]],
    ]

    t = Table(data, colWidths=[180, 300])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
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
    secundarios = [c for c in cables if _tipo_norm(c) == "BT"]

    if primarios:
        total = sum(_float_safe(c.get("Longitud", 0)) for c in primarios)
        lineas.append(f"Construcción de {total:.0f} m de línea primaria.")

    if secundarios:
        total = sum(_float_safe(c.get("Longitud", 0)) for c in secundarios)
        lineas.append(f"Construcción de {total:.0f} m de línea secundaria.")

    if not lineas:
        lineas.append("No se cuenta con información suficiente para describir el proyecto.")

    texto = "<br/>".join([f"{i+1}. {l}" for i, l in enumerate(lineas)])

    return [
        Paragraph("<b>Descripción general del Proyecto:</b>", styleN),
        Spacer(1, 6),
        Paragraph(texto, styleN),
        Spacer(1, 18),
    ]


# ==========================================================
# FUNCIÓN PRINCIPAL
# ==========================================================
def hoja_info_proyecto(
    datos_proyecto,
    df_estructuras=None,
    df_mat=None,
    *,
    styleN=None,
    styleH=None,
):

    styles = getSampleStyleSheet()
    styleN = styleN or styles["Normal"]
    styleH = styleH or styles["Heading1"]

    # 🔥 NORMALIZAR
    datos_proyecto = _normalizar_datos(datos_proyecto)

    # 🔥 INYECTAR CABLES DESDE MATERIALES
    if df_mat is not None and not df_mat.empty:
        datos_proyecto["cables_proyecto"] = df_mat.to_dict(orient="records")

    tension_fmt = _formato_tension(datos_proyecto["tension"])
    cables = datos_proyecto["cables_proyecto"]

    elems = []

    elems.append(Paragraph("<b>Hoja de Información del Proyecto</b>", styleH))
    elems.append(Spacer(1, 12))

    elems.extend(build_tabla(datos_proyecto, cables, tension_fmt, styleN))
    elems.extend(build_descripcion(datos_proyecto, df_estructuras, cables, styleN))

    return elems


# ==========================================================
# WRAPPER LIMPIO
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
    )
