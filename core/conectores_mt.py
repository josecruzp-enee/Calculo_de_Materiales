# -*- coding: utf-8 -*-
"""
core/conectores_mt.py
Reemplazo robusto de conectores de compresión por calibre (simétricos X-X).
"""

from __future__ import annotations
import re
import unicodedata
from typing import Optional, Sequence
import pandas as pd

# ---------- normalizadores ----------
def _strip_accents(s: str) -> str:
    s = str(s or "")
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))

def _nrm(s: str) -> str:
    s = _strip_accents(str(s or ""))
    s = re.sub(r"\s+", " ", s).strip().upper()
    return s

def _nrm_no_spaces(s: str) -> str:
    return _nrm(s).replace(" ", "")

def _norm_num_token(tok: str) -> str:
    t = _nrm_no_spaces(tok)
    t = t.replace(",", ".")  # 266,8 -> 266.8
    for suf in ("ASCR", "AAC", "MCM", "AWG", "WP"):
        t = t.replace(suf, "")
    return t

def _calibre_norm(calibre: str) -> str:
    return _norm_num_token(calibre)

def _familia_estructura(codigo: str) -> str:
    c = _nrm_no_spaces(codigo)
    return re.split(r"[-/ ]", c, 1)[0] if c else c

# ---------- carga conectores ----------
_PATRON_PAREJA = re.compile(r"\(\s*([^\s()]+)\s*[-–]\s*([^\s()]+)\s*\)")

def _extrae_simetrico_norm(descripcion: str) -> Optional[str]:
    if not descripcion:
        return None
    m = _PATRON_PAREJA.search(descripcion)
    if not m:
        return None
    a, b = m.group(1), m.group(2)
    a = _norm_num_token(a)
    b = _norm_num_token(b)
    return f"{a}-{b}"

def cargar_conectores_mt(archivo_materiales: str) -> pd.DataFrame:
    try:
        df = pd.read_excel(archivo_materiales, sheet_name="conectores")
    except Exception as e:
        print(f"⚠️ No se pudo cargar hoja 'conectores': {e}")
        return pd.DataFrame(columns=[
            "Calibre", "Código", "Descripción", "Estructuras aplicables",
            "SIMETRICO_NORM", "APLICABLES_TOKENS"
        ])

    # renombres flexibles
    ren = {}
    for col in df.columns:
        k = _nrm(col)
        if k in ("DESCRIPCION", "DESCRIPCIÓN"): ren[col] = "Descripción"
        elif k in ("CODIGO", "CÓDIGO"): ren[col] = "Código"
        elif k == "ESTRUCTURAS APLICABLES": ren[col] = "Estructuras aplicables"
        elif k == "CALIBRE": ren[col] = "Calibre"
    if ren:
        df = df.rename(columns=ren)

    for col in ("Calibre", "Código", "Descripción", "Estructuras aplicables"):
        if col not in df.columns:
            df[col] = ""

    df["Descripción"] = df["Descripción"].astype(str)
    df["SIMETRICO_NORM"] = df["Descripción"].apply(_extrae_simetrico_norm)

    def _tok_aplicables(x: str):
        if not x: return []
        toks = re.split(r"[;,/| ]+", str(x))
        toks = [_nrm_no_spaces(t) for t in toks if t.strip()]
        return toks

    if "Estructuras aplicables" not in df.columns:
        df["Estructuras aplicables"] = ""
    df["APLICABLES_TOKENS"] = df["Estructuras aplicables"].apply(_tok_aplicables)

    return df[[
        "Calibre", "Código", "Descripción",
        "Estructuras aplicables",
        "SIMETRICO_NORM", "APLICABLES_TOKENS"
    ]]

# ---------- búsqueda ----------
def _coincide_familia(tokens: list[str], familia: Optional[str]) -> bool:
    if not familia:
        return True
    return _nrm_no_spaces(familia) in (tokens or [])

def buscar_conector_mt(
    calibre: str,
    tabla_conectores: pd.DataFrame,
    familia_estructura: Optional[str] = None
) -> Optional[str]:
    if tabla_conectores.empty or not calibre:
        return None

    cn = _calibre_norm(calibre)        # '266.8'
    clave = f"{cn}-{cn}"               # '266.8-266.8'

    # índice simétrico (preferido)
    mask = (tabla_conectores["SIMETRICO_NORM"] == clave)
    if familia_estructura:
        mask &= tabla_conectores["APLICABLES_TOKENS"].apply(
            lambda toks: _coincide_familia(toks, familia_estructura)
        )
    candidatos = tabla_conectores.loc[mask]
    if not candidatos.empty:
        return candidatos.iloc[0]["Descripción"]

    # fallback: patrón en texto
    patron = re.compile(rf"\(\s*{re.escape(cn)}\s*[-–]\s*{re.escape(cn)}\s*\)")
    for _, fila in tabla_conectores.iterrows():
        desc = _strip_accents(str(fila.get("Descripción", ""))).replace(",", ".")
        if patron.search(desc):
            if _coincide_familia(fila.get("APLICABLES_TOKENS", []), familia_estructura):
                return fila.get("Descripción")

    return None

# ---------- reemplazo ----------
def aplicar_reemplazos_conectores(
    lista_materiales: Sequence[str],
    calibre_estructura: str,
    tabla_conectores: pd.DataFrame,
    codigo_estructura: Optional[str] = None,
) -> list[str]:
    familia = _familia_estructura(codigo_estructura) if codigo_estructura else None
    out: list[str] = []
    for mat in lista_materiales:
        n = _nrm(mat)
        if "CONECTOR" in n and "COMPRESION" in n:  # COMPRESIÓN/COMPRESION neutralizado
            nuevo = buscar_conector_mt(calibre_estructura, tabla_conectores, familia_estructura=familia)
            if nuevo:
                out.append(nuevo)
                continue
        out.append(mat)
    return out

