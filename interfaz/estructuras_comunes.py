# interfaz/estructuras_comunes.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import List
import io
import os
import re
import time
import tempfile

import pandas as pd
import streamlit as st


# =============================================================================
# Esquema base (ANCHO) que ve el usuario en la UI
# =============================================================================
COLUMNAS_BASE: List[str] = [
    "Punto",
    "Poste",
    "Primario",
    "Secundario",
    "Retenidas",
    "Conexiones a tierra",
    "Transformadores",
    "Luminarias",
]


# =============================================================================
# Utilidades de normalización / parseo
# =============================================================================
def normalizar_columnas(df: pd.DataFrame, columnas: List[str] = COLUMNAS_BASE) -> pd.DataFrame:
    """Asegura todas las columnas requeridas en orden ANCHO y renombra variantes comunes."""
    df = df.copy()
    df = df.rename(columns={
        "Retenida": "Retenidas",
        "Aterrizaje": "Conexiones a tierra",
        "Transformador": "Transformadores",
    })
    for c in columnas:
        if c not in df.columns:
            df[c] = ""
    return df[columnas]


def norm_code_value(s: str) -> str:
    """Limpia código de estructura: recorta y quita sufijos finales '(E)/(P)/(R)'."""
    if pd.isna(s):
        return ""
    s = str(s).strip()
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s).strip()
    return s


def split_cell_items(cell: str) -> List[str]:
    """Separa una celda por coma, punto y coma o saltos de línea (maneja comillas)."""
    if not isinstance(cell, str):
        return []
    s = cell.strip().strip('"').strip("'")
    if not s or s == "-":
        return []
    parts = re.split(r'[,;\n\r]+', s)
    return [p.strip() for p in parts if p.strip()]


def parse_item(piece: str) -> tuple[str, int]:
    """
    Interpreta cantidad + código. Soporta:
      - '2× R-1' / '2x R-1'
      - '2 R-1'
      - '2B-I-4'  (cantidad pegada al código)
      - 'A-I-4 (E)' (cantidad implícita 1)
    """
    m = re.match(r'^(\d+)\s*[x×]\s*(.+)$', piece, flags=re.I)   # 2x CODE
    if m:
        return norm_code_value(m.group(2)), int(m.group(1))
    m = re.match(r'^(\d+)\s+(.+)$', piece)                      # 2 CODE
    if m:
        return norm_code_value(m.group(2)), int(m.group(1))
    m = re.match(r'^(\d+)([A-Za-z].+)$', piece)                 # 2CODE
    if m:
        return norm_code_value(m.group(2)), int(m.group(1))
    return norm_code_value(piece), 1


# =============================================================================
# Transformaciones (ANCHO -> LARGO) + materialización a Excel temporal
# =============================================================================
def expand_wide_to_long(df_ancho: pd.DataFrame) -> pd.DataFrame:
    """
    ANCHO -> LARGO para el motor de reportes.
    Devuelve columnas: Punto, codigodeestructura, cantidad
    """
    df = normalizar_columnas(df_ancho, COLUMNAS_BASE).copy()
    cat_cols = [
        "Poste", "Primario", "Secundario",
        "Retenidas", "Conexiones a tierra",
        "Transformadores", "Luminarias",
    ]
    rows = []
    for _, r in df.iterrows():
        punto = str(r.get("Punto", "")).strip()
        for col in cat_cols:
            for piece in split_cell_items(str(r.get(col, "") or "")):
                code, qty = parse_item(piece)
                if code:
                    rows.append({
                        "Punto": punto,
                        "codigodeestructura": code,   # EXACTO como lo exige el generador
                        "cantidad": int(qty),
                    })
    return pd.DataFrame(rows, columns=["Punto", "codigodeestructura", "cantidad"])


def materializar_df_a_archivo(df_ancho: pd.DataFrame, etiqueta: str = "data") -> str:
    """
    Crea un .xlsx temporal con:
      • Hoja 'estructuras'       -> LARGO (Punto, codigodeestructura, cantidad)  [PRIMERA]
      • Hoja 'estructuras_ancha' -> ANCHO (para inspección en la UI)
    """
    ts = int(time.time())
    ruta = os.path.join(tempfile.gettempdir(), f"estructuras_{etiqueta}_{ts}.xlsx")

    df_ancho_norm = normalizar_columnas(df_ancho, COLUMNAS_BASE)
    df_largo = expand_wide_to_long(df_ancho_norm)

    try:
        writer = pd.ExcelWriter(ruta, engine="openpyxl")
    except Exception:
        writer = pd.ExcelWriter(ruta, engine="xlsxwriter")

    with writer:
        df_largo.to_excel(writer, sheet_name="estructuras", index=False)
        df_ancho_norm.to_excel(writer, sheet_name="estructuras_ancha", index=False)

    # Debug mínimo útil (opcional)
    try:
        xls = pd.ExcelFile(ruta)
        hoja = next((s for s in xls.sheet_names if s.lower() == "estructuras"), xls.sheet_names[0])
        cols = list(pd.read_excel(xls, sheet_name=hoja, nrows=0).columns)
        st.caption("🔎 Estructuras generadas (debug)")
        st.write({"ruta": ruta, "hojas": xls.sheet_names, "columnas_estructuras": cols})
    except Exception:
        pass

    return ruta


# =============================================================================
# Texto -> DataFrame ANCHO (para modo "pegar tabla")
# =============================================================================
def parsear_texto_a_df(texto: str, columnas: List[str] = COLUMNAS_BASE) -> pd.DataFrame:
    """Convierte texto pegado (CSV/TSV/; o | o whitespace) a DataFrame ANCHO."""
    txt = (texto or "").strip()
    if not txt:
        return pd.DataFrame(columns=columnas)

    df = None
    for sep in ("\t", ",", ";", "|"):
        try:
            df = pd.read_csv(io.StringIO(txt), sep=sep)
            break
        except Exception:
            df = None

    if df is None:
        try:
            df = pd.read_csv(io.StringIO(txt), delim_whitespace=True)
        except Exception:
            return pd.DataFrame(columns=columnas)

    return normalizar_columnas(df, columnas)
