# -*- coding: utf-8 -*-
"""
hoja_info.py (VERSIÓN CORREGIDA Y ROBUSTA)
"""

from __future__ import annotations

import re
from datetime import datetime
from math import sqrt, floor
from typing import Dict, List, Optional, Tuple

import pandas as pd
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors


# ==========================================================
# ✅ NORMALIZADOR LOCAL (SIN DEPENDENCIAS EXTERNAS)
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
# ✅ VALIDACIÓN
# ==========================================================

def _validar_df(df, nombre, columnas):
    if df is None:
        raise ValueError(f"{nombre} es None")

    faltantes = [c for c in columnas if c not in df.columns]
    if faltantes:
        raise ValueError(f"{nombre} no tiene columnas: {faltantes}")


def _validar_dependencias(styleH, styleN, calibres_fn):
    if styleH is None or styleN is None or calibres_fn is None:
        raise ValueError("Faltan estilos o función de calibres")


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


# ==========================================================
# EXTRACTORES
# ==========================================================

def extraer_postes(df_estructuras):

    df_estructuras = normalizar_df(df_estructuras)

    if df_estructuras is None or df_estructuras.empty:
        return None, 0

    _validar_df(df_estructuras, "df_estructuras", ["CodigoEstructura", "Cantidad"])

    s = df_estructuras["CodigoEstructura"].astype(str)

    postes = df_estructuras[s.str.contains(r"^(PC|PM|PT)-", case=False, na=False)]

    if postes.empty:
        return None, 0

    resumen = {}
    for _, r in postes.iterrows():
        cod = str(r["CodigoEstructura"])
        cant = int(_float_safe(r["Cantidad"]))
        resumen[cod] = resumen.get(cod, 0) + cant

    return resumen, sum(resumen.values())


def extraer_transformadores(df_estructuras, df_mat):

    df_estructuras = normalizar_df(df_estructuras)

    if df_estructuras is None or df_estructuras.empty:
        return 0, "", []

    if "CodigoEstructura" not in df_estructuras.columns:
        return 0, "", []

    s = df_estructuras["CodigoEstructura"].astype(str).str.upper()

    # 🔍 Extraer solo transformadores
    ext = s.str.extract(r"^(TS|TD|TT)-(\d+(?:\.\d+)?)KVA", expand=True)

    mask = ext[0].notna()
    if not mask.any():
        return 0, "", []

    qty = pd.to_numeric(
        df_estructuras.loc[mask, "Cantidad"],
        errors="coerce"
    ).fillna(0)

    bancos = {}
    mult = {"TS": 1, "TD": 2, "TT": 3}

    # 🔥 LOOP CORREGIDO (ANTI-NaN)
    for p, k, q in zip(ext[0], ext[1], qty):

        # ignorar basura
        if pd.isna(p) or pd.isna(k):
            continue

        key = f"{p}-{k} kVA"
        bancos[key] = bancos.get(key, 0) + int(q)

    # 🔥 limpieza extra (doble protección)
    bancos = {
        k: v for k, v in bancos.items()
        if k and str(k).strip().lower() != "nan"
    }

    # 🔥 cálculo seguro
    total = sum(
        v * mult.get(k.split("-")[0], 0)
        for k, v in bancos.items()
    )

    resumen = " + ".join([
        f"{v} x {k}" for k, v in bancos.items()
    ])

    return total, resumen, list(bancos.keys())

def extraer_luminarias(df_estructuras, df_mat):

    df_estructuras = normalizar_df(df_estructuras)

    if df_estructuras is None or df_estructuras.empty:
        return 0, {}

    if "CodigoEstructura" not in df_estructuras.columns:
        return 0, {}

    s = df_estructuras["CodigoEstructura"].astype(str)

    mask = s.str.contains(r"^LL-\d+-", case=False, na=False)

    if not mask.any():
        return 0, {}

    qty = pd.to_numeric(df_estructuras.loc[mask, "Cantidad"], errors="coerce").fillna(0)

    det = {}
    for cod, q in zip(s[mask], qty):
        m = re.search(r"(\d+)W", cod)
        pot = f"{m.group(1)} W" if m else "SIN POTENCIA"
        det[pot] = det.get(pot, 0) + int(q)

    return sum(det.values()), det


# ==========================================================
# BUILDERS
# ==========================================================

def build_header(styleH):
    return [
        Paragraph("<b>Hoja de Información del Proyecto</b>", styleH),
        Spacer(1, 12),
    ]


def build_tabla_datos(datos_proyecto, styleN):

    data = [
        ["Nombre del Proyecto:", datos_proyecto.get("nombre_proyecto", "")],
        ["Código:", datos_proyecto.get("codigo_proyecto", "")],
        ["Fecha:", datos_proyecto.get("fecha_informe", datetime.today().strftime("%Y-%m-%d"))],
    ]

    t = Table(data, colWidths=[180, 300])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
    ]))

    return [t, Spacer(1, 18)]


def build_descripcion(df_estructuras, df_mat, styleN):

    lineas = []

    resumen_postes, total_postes = extraer_postes(df_estructuras)
    if resumen_postes:
        lineas.append(f"Instalación de {total_postes} postes.")

    total_t, resumen_t, _ = extraer_transformadores(df_estructuras, df_mat)
    if total_t:
        lineas.append(f"{total_t} transformadores ({resumen_t}).")

    total_l, det_l = extraer_luminarias(df_estructuras, df_mat)
    if total_l:
        lineas.append(f"{total_l} luminarias.")

    texto = "<br/>".join([f"{i+1}. {l}" for i, l in enumerate(lineas)])

    return [
        Paragraph("<b>Descripción del Proyecto</b>", styleN),
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
    _calibres_por_tipo=None,
):

    _validar_dependencias(styleH, styleN, _calibres_por_tipo)

    elems = []

    elems.extend(build_header(styleH))
    elems.extend(build_tabla_datos(datos_proyecto, styleN))
    elems.extend(build_descripcion(df_estructuras, df_mat, styleN))

    return elems
