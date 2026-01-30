# interfaz/estructuras_comunes.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import List, Dict, Tuple
import io
import os
import re
import time
import tempfile
import unicodedata

import pandas as pd


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

CAT_COLS: List[str] = [
    "Poste",
    "Primario",
    "Secundario",
    "Retenidas",
    "Conexiones a tierra",
    "Transformadores",
    "Luminarias",
]


# =============================================================================
# Normalización de encabezados (ÚNICA etapa donde se toleran variantes)
# =============================================================================
def _strip_accents(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in s if not unicodedata.combining(c))


def _norm_header(s: str) -> str:
    """
    Normaliza SOLO el nombre del encabezado:
    - quita tildes
    - colapsa espacios
    - lower
    """
    s = _strip_accents(str(s)).strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


# Variantes -> canónico
_MAPA_COLUMNAS: Dict[str, str] = {
    # Punto
    "punto": "Punto",
    "punto #": "Punto",
    "punto#": "Punto",

    # Poste
    "poste": "Poste",

    # Primario / Secundario
    "primario": "Primario",
    "secundario": "Secundario",

    # Retenidas
    "retenida": "Retenidas",
    "retenidas": "Retenidas",

    # Tierra / aterrizaje
    "aterrizaje": "Conexiones a tierra",
    "conexion a tierra": "Conexiones a tierra",
    "conexiones a tierra": "Conexiones a tierra",
    "conexiones a tierra ": "Conexiones a tierra",

    # Transformadores
    "transformador": "Transformadores",
    "transformadores": "Transformadores",

    # Luminarias
    "luminaria": "Luminarias",
    "luminarias": "Luminarias",
}


def normalizar_columnas(df: pd.DataFrame, columnas: List[str] = COLUMNAS_BASE) -> pd.DataFrame:
    """
    1) Renombra variantes comunes -> nombres canónicos
    2) Garantiza columnas requeridas (rellena con "")
    3) Reordena en el orden canónico
    """
    if df is None:
        return pd.DataFrame(columns=columnas)

    df = df.copy()

    # Renombrar usando mapa normalizado de encabezados
    rename: Dict[str, str] = {}
    for col in list(df.columns):
        key = _norm_header(col)
        if key in _MAPA_COLUMNAS:
            rename[col] = _MAPA_COLUMNAS[key]

    if rename:
        df = df.rename(columns=rename)

    # Asegura todas las columnas canónicas
    for c in columnas:
        if c not in df.columns:
            df[c] = ""

    # Reorden final
    return df[columnas]


# =============================================================================
# Utilidades de parseo
# =============================================================================
def norm_code_value(s: str) -> str:
    """Limpia código: recorta y quita sufijos finales '(E)/(P)/(R)/(D)'."""
    if pd.isna(s):
        return ""
    s = str(s).strip()
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s).strip()
    return s


def split_cell_items(cell: str) -> List[str]:
    """
    Separa por coma, ; o saltos de línea.
    Repara caso: "A-I-4, (E)" -> pega "(E)" al item anterior.
    """
    if not isinstance(cell, str):
        return []

    s = cell.strip().strip('"').strip("'")
    if not s or s == "-":
        return []

    parts = re.split(r"[,;\n\r]+", s)
    parts = [p.strip() for p in parts if p and p.strip()]

    fixed: List[str] = []
    for p in parts:
        if re.fullmatch(r"\(\s*[pPeErRdD]\s*\)", p):
            if fixed:
                fixed[-1] = f"{fixed[-1]} {p}"
            else:
                fixed.append(p)
        else:
            fixed.append(p)

    return fixed


def es_proyectada(piece: str) -> bool:
    """True si contiene (P) al final, incluso pegado tipo B-II-4C(P)."""
    if not isinstance(piece, str):
        return False
    txt = piece.strip()
    return re.search(r"\(\s*p\s*\)\s*$", txt, flags=re.I) is not None


def parse_item(piece: str) -> Tuple[str, int]:
    """
    Soporta:
      - '2× R-1' / '2x R-1'
      - '2 R-1'
      - '2B-I-4'
      - 'A-I-4 (E)'
    """
    piece = (piece or "").strip()

    m = re.match(r"^(\d+)\s*[x×]\s*(.+)$", piece, flags=re.I)
    if m:
        return norm_code_value(m.group(2)), int(m.group(1))

    m = re.match(r"^(\d+)\s+(.+)$", piece)
    if m:
        return norm_code_value(m.group(2)), int(m.group(1))

    m = re.match(r"^(\d+)([A-Za-z].+)$", piece)
    if m:
        return norm_code_value(m.group(2)), int(m.group(1))

    return norm_code_value(piece), 1


# =============================================================================
# Transformación ANCHO -> LARGO (motor)
# =============================================================================
def expand_wide_to_long(df_ancho: pd.DataFrame, solo_proyectadas: bool = True) -> pd.DataFrame:
    """
    Devuelve columnas: Punto, codigodeestructura, cantidad.

    Regla (P):
    - Si solo_proyectadas=True y el DF tiene marcas (P) en alguna celda => filtra por (P)
    - Si no hay ninguna marca (P) en todo el DF => NO filtra (asume ya filtrado)
    """
    df = normalizar_columnas(df_ancho, COLUMNAS_BASE).copy()

    hay_marca_p = False
    if solo_proyectadas:
        for col in CAT_COLS:
            s = df[col].astype(str)
            if s.str.contains(r"\(\s*p\s*\)", case=False, regex=True).any():
                hay_marca_p = True
                break

    rows = []
    for _, r in df.iterrows():
        punto = str(r.get("Punto", "")).strip()

        for col in CAT_COLS:
            cell = str(r.get(col, "") or "")
            for piece in split_cell_items(cell):
                if solo_proyectadas and hay_marca_p and not es_proyectada(piece):
                    continue

                code, qty = parse_item(piece)
                if code:
                    rows.append(
                        {
                            "Punto": punto,
                            "codigodeestructura": code,
                            "cantidad": int(qty),
                        }
                    )

    return pd.DataFrame(rows, columns=["Punto", "codigodeestructura", "cantidad"])


# =============================================================================
# Materialización a Excel temporal (sin Streamlit)
# =============================================================================
def materializar_df_a_archivo(df_ancho: pd.DataFrame, etiqueta: str = "data") -> str:
    """
    Crea un .xlsx temporal con:
      • Hoja 'estructuras'       -> LARGO (Punto, codigodeestructura, cantidad)
      • Hoja 'estructuras_ancha' -> ANCHO normalizado
    """
    ts = int(time.time())
    ruta = os.path.join(tempfile.gettempdir(), f"estructuras_{etiqueta}_{ts}.xlsx")

    df_ancho_norm = normalizar_columnas(df_ancho, COLUMNAS_BASE)
    df_largo = expand_wide_to_long(df_ancho_norm, solo_proyectadas=True)

    try:
        writer = pd.ExcelWriter(ruta, engine="openpyxl")
    except Exception:
        writer = pd.ExcelWriter(ruta, engine="xlsxwriter")

    with writer:
        df_largo.to_excel(writer, sheet_name="estructuras", index=False)
        df_ancho_norm.to_excel(writer, sheet_name="estructuras_ancha", index=False)

    return ruta


# =============================================================================
# Texto -> DataFrame ANCHO
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
