# -*- coding: utf-8 -*-
"""
hoja_info.py (VERSIÓN PRO COMPLETA - FIX COLUMNAS)
"""

from __future__ import annotations

import re
from datetime import datetime
from math import sqrt, floor
from typing import Optional

import pandas as pd
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors


# ==========================================================
# NORMALIZADOR
# ==========================================================

COLUMN_MAP = {
    "codigodeestructura": "CodigoEstructura",
    "codigo": "CodigoEstructura",
    "cod": "CodigoEstructura",
    "materiales": "Materiales",
    "material": "Materiales",
    "cantidad": "Cantidad",
    "cant": "Cantidad",
    "punto": "Punto",
    "unidad": "Unidad",
}


def normalizar_df(df: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
    if df is None or df.empty:
        return df

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    rename = {}
    for c in df.columns:
        key = c.lower().replace(" ", "")
        if key in COLUMN_MAP:
            rename[c] = COLUMN_MAP[key]

    return df.rename(columns=rename)


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
        vln = floor((vll / sqrt(3)) * 10) / 10
        return f"{vln:.1f} LN / {vll:.1f} LL KV"
    except:
        return str(vll)


def _get_col_estructura(df):
    """🔥 CLAVE: detecta automáticamente la columna correcta"""
    if "CodigoEstructura" in df.columns:
        return "CodigoEstructura"
    elif "Estructura" in df.columns:
        return "Estructura"
    else:
        return None


# ==========================================================
# EXTRACTORES
# ==========================================================

def extraer_postes(df_estructuras):
    df_estructuras = normalizar_df(df_estructuras)

    if df_estructuras is None or df_estructuras.empty:
        return None, 0

    col = _get_col_estructura(df_estructuras)
    if col is None:
        return None, 0

    s = df_estructuras[col].astype(str)

    postes = df_estructuras[s.str.contains(r"^(PC|PM|PT)", case=False, na=False)]

    if postes.empty:
        return None, 0

    total = postes["Cantidad"].apply(_float_safe).sum()

    return None, int(total)


def extraer_transformadores(df_estructuras, df_mat):
    df_estructuras = normalizar_df(df_estructuras)

    if df_estructuras is None or df_estructuras.empty:
        return 0, "", []

    col = _get_col_estructura(df_estructuras)
    if col is None:
        return 0, "", []

    s = df_estructuras[col].astype(str).str.upper()

    # 🔥 MÁS FLEXIBLE
    ext = s.str.extract(r"(TS|TD|TT).*?(\d+)", expand=True)

    mask = ext[0].notna()
    if not mask.any():
        return 0, "", []

    qty = pd.to_numeric(
        df_estructuras.loc[mask, "Cantidad"],
        errors="coerce"
    ).fillna(0)

    bancos = {}

    for p, k, q in zip(ext[0], ext[1], qty):
        key = f"{p}-{k} kVA"
        bancos[key] = bancos.get(key, 0) + int(q)

    resumen = ", ".join([f"{v} x {k}" for k, v in bancos.items()])

    total = sum(bancos.values())

    return total, resumen, list(bancos.keys())


def extraer_luminarias(df_estructuras, df_mat):
    df_estructuras = normalizar_df(df_estructuras)

    if df_estructuras is None or df_estructuras.empty:
        return 0, {}

    col = _get_col_estructura(df_estructuras)
    if col is None:
        return 0, {}

    s = df_estructuras[col].astype(str)

    mask = s.str.contains(r"LL", case=False, na=False)

    if not mask.any():
        return 0, {}

    qty = pd.to_numeric(
        df_estructuras.loc[mask, "Cantidad"],
        errors="coerce"
    ).fillna(0)

    det = {}
    for cod, q in zip(s[mask], qty):
        m = re.search(r"(\d+)W", cod)
        pot = f"{m.group(1)} W" if m else "SIN POTENCIA"
        det[pot] = det.get(pot, 0) + int(q)

    return sum(det.values()), det


def extraer_cables(df_cables):
    if df_cables is None or df_cables.empty:
        return 0, {}

    if "Cantidad" not in df_cables.columns:
        return 0, {}

    total = float(df_cables["Cantidad"].sum())

    det = {}
    for _, r in df_cables.iterrows():
        mat = str(r.get("Materiales", ""))
        qty = float(r.get("Cantidad", 0))
        det[mat] = det.get(mat, 0) + qty

    return total, det


# ==========================================================
# BUILDERS
# ==========================================================

def build_header(styleH):
    return [
        Paragraph("<b>Hoja de Información del Proyecto</b>", styleH),
        Spacer(1, 12),
    ]


def build_tabla_datos(datos_proyecto, styleN):

    tension = (
        datos_proyecto.get("nivel_tension")
        or datos_proyecto.get("nivel_de_tension")
        or datos_proyecto.get("tension", "")
    )

    data = [
        ["Nombre del Proyecto:", datos_proyecto.get("nombre_proyecto", "")],
        ["Código / Expediente:", datos_proyecto.get("codigo_proyecto", "")],
        ["Nivel de Tensión:", _formato_tension(tension)],
        ["Calibre Primario:", datos_proyecto.get("calibre_mt", "")],
        ["Fecha de Informe:", datos_proyecto.get("fecha_informe", datetime.today().strftime("%Y-%m-%d"))],
        ["Responsable:", datos_proyecto.get("responsable", "")],
        ["Empresa:", datos_proyecto.get("empresa", "")],
    ]

    t = Table(data, colWidths=[220, 280])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
    ]))

    return [t, Spacer(1, 18)]


def build_descripcion(df_estructuras, df_mat, styleN, df_cables=None):

    partes = []

    _, total_postes = extraer_postes(df_estructuras)
    if total_postes:
        partes.append(f"{total_postes} postes")

    total_t, resumen_t, _ = extraer_transformadores(df_estructuras, df_mat)
    if total_t:
        partes.append(f"{resumen_t} en transformadores")

    total_l, det_l = extraer_luminarias(df_estructuras, df_mat)
    if total_l:
        detalle_l = ", ".join([f"{v} de {k}" for k, v in det_l.items()])
        partes.append(f"{detalle_l} en luminarias")

    total_c, det_c = extraer_cables(df_cables)
    if total_c:
        detalle_c = ", ".join([f"{round(v,1)} de {k}" for k, v in det_c.items()])
        partes.append(f"{detalle_c} en conductores")

    if partes:
        texto = "Proyecto que contempla la instalación de " + ", ".join(partes) + "."
    else:
        texto = "Proyecto sin elementos detectados automáticamente."

    return [
        Paragraph("<b>Descripción general del Proyecto</b>", styleN),
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
    df_cables=None,
    *,
    styleN=None,
    styleH=None,
    _calibres_por_tipo=None,
):
    df_cables = df_cables if df_cables is not None else df_mat
    elems = []

    elems.extend(build_header(styleH))
    elems.extend(build_tabla_datos(datos_proyecto, styleN))
    elems.extend(build_descripcion(df_estructuras, df_mat, styleN, df_cables))

    return elems
