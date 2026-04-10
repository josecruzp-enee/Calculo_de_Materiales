# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from datetime import datetime
from math import sqrt, floor
from typing import Optional

import pandas as pd
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors


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
        return f"{vln:.1f} / {vll:.1f} kV"
    except:
        return str(vll)


def _get_col_estructura(df):
    if "CodigoEstructura" in df.columns:
        return "CodigoEstructura"
    elif "Estructura" in df.columns:
        return "Estructura"
    return None


# ==========================================================
# EXTRACTORES
# ==========================================================

def extraer_postes(df):
    if df is None or df.empty:
        return 0, {}

    col = _get_col_estructura(df)
    if col is None:
        return 0, {}

    s = df[col].astype(str)

    postes = df[s.str.contains(r"^(PC|PM|PT)", case=False, na=False)]

    if postes.empty:
        return 0, {}

    agrupado = postes.groupby(col)["Cantidad"].sum()
    total = int(postes["Cantidad"].apply(_float_safe).sum())

    return total, agrupado.to_dict()


def extraer_transformadores(df):
    if df is None or df.empty:
        return 0, ""

    col = _get_col_estructura(df)
    if col is None:
        return 0, ""

    s = df[col].astype(str).str.upper()

    ext = s.str.extract(r"(TS|TD|TT).*?(\d+)", expand=True)

    mask = ext[0].notna()
    if not mask.any():
        return 0, ""

    qty = pd.to_numeric(df.loc[mask, "Cantidad"], errors="coerce").fillna(0)

    bancos = {}

    for p, k, q in zip(ext[0], ext[1], qty):
        key = f"{p}-{k} kVA"
        bancos[key] = bancos.get(key, 0) + int(q)

    resumen = ", ".join([f"{v} x {k}" for k, v in bancos.items()])

    return sum(bancos.values()), resumen


def extraer_luminarias(df):
    if df is None or df.empty:
        return 0, {}

    col = _get_col_estructura(df)
    if col is None:
        return 0, {}

    s = df[col].astype(str)

    mask = s.str.contains(r"LL", case=False, na=False)

    if not mask.any():
        return 0, {}

    qty = pd.to_numeric(df.loc[mask, "Cantidad"], errors="coerce").fillna(0)

    det = {}
    for cod, q in zip(s[mask], qty):
        m = re.search(r"(\d+)W", cod)
        pot = f"{m.group(1)} W" if m else "SIN POTENCIA"
        det[pot] = det.get(pot, 0) + int(q)

    return sum(det.values()), det


def extraer_conductor(df_mat):
    if df_mat is None or df_mat.empty:
        return 0, ""

    if "Materiales" not in df_mat.columns:
        return 0, ""

    df = df_mat.copy()

    mask = df["Materiales"].str.contains(
        r"ACSR|AAAC|ALUMINIO|COBRE|CABLE",
        case=False,
        na=False
    )

    df = df[mask]

    if df.empty:
        return 0, ""

    agrupado = df.groupby("Materiales")["Cantidad"].sum().sort_values(ascending=False)

    return float(agrupado.iloc[0]), agrupado.index[0]


# ==========================================================
# TABLA DE DATOS (CLAVE)
# ==========================================================

def build_tabla_datos(datos, styleN):

    tension = (
        datos.get("nivel_tension")
        or datos.get("nivel_de_tension")
        or datos.get("tension")
    )

    data = [
        ["Nombre del Proyecto:", datos.get("nombre_proyecto", "")],
        ["Código / Expediente:", datos.get("codigo_proyecto", "")],
        ["Nivel de Tensión (kV):", _formato_tension(tension)],
        ["Calibre Primario:", datos.get("calibre_mt", "")],
        ["Calibre Secundario:", datos.get("calibre_bt", "")],
        ["Calibre Neutro:", datos.get("calibre_neutro", "")],
        ["Calibre Piloto:", datos.get("calibre_piloto", "")],
        ["Cable de Retenidas:", datos.get("retenida", "")],
        ["Fecha de Informe:", datos.get("fecha_informe", datetime.today().strftime("%Y-%m-%d"))],
        ["Responsable / Diseñador:", datos.get("responsable", "")],
        ["Empresa / Área:", datos.get("empresa", "")],
    ]

    t = Table(data, colWidths=[230, 260])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
    ]))

    return [t, Spacer(1, 15)]


# ==========================================================
# DESCRIPCIÓN (FORMATO ORIGINAL)
# ==========================================================

def build_descripcion(df_estructuras, df_mat, styleN):

    lines = []

    # 1. POSTES
    total_postes, det_postes = extraer_postes(df_estructuras)
    if total_postes:
        detalle = ", ".join([f"{int(v)} {k}" for k, v in det_postes.items()])
        lines.append(f"1. Hincado de {detalle} (Total: {total_postes} postes).")

    # 2. CONDUCTORES
    total_c, tipo_c = extraer_conductor(df_mat)
    if total_c:
        lines.append(f"2. Construcción de {int(total_c)} m con conductor {tipo_c}.")

    # 3. TRANSFORMADORES
    total_t, resumen_t = extraer_transformadores(df_estructuras)
    if total_t:
        lines.append(f"3. Instalación de {total_t} transformador(es) en conexión {resumen_t}.")

    # 4. LUMINARIAS
    total_l, det_l = extraer_luminarias(df_estructuras)
    if total_l:
        detalle_l = ", ".join([f"{v} de {k}" for k, v in det_l.items()])
        lines.append(f"4. Instalación de {total_l} luminaria(s) ({detalle_l}).")

    elems = [
        Paragraph("<b>Descripción general del Proyecto:</b>", styleN),
        Spacer(1, 6),
    ]

    for l in lines:
        elems.append(Paragraph(l, styleN))

    elems.append(Spacer(1, 12))

    return elems


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
    _calibres_por_tipo=None,
):

    elems = []

    elems.append(Paragraph("<b>Hoja de Información del Proyecto</b>", styleH))
    elems.append(Spacer(1, 12))

    elems.extend(build_tabla_datos(datos_proyecto, styleN))
    elems.extend(build_descripcion(df_estructuras, df_mat, styleN))

    return elems
