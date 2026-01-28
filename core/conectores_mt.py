# -*- coding: utf-8 -*-
"""
core/conectores_mt.py

Regla:
- Reemplazar SOLO en estructuras MT: A, TH, ER, TM
- SOLO si calibre_estructura != 1/0
- Reemplazar SOLO conectores de compresión YC/YPC
- Si el material ya trae (X-Y) en paréntesis => NO tocar
"""

from __future__ import annotations
import re
import unicodedata
from typing import Optional, List
import pandas as pd


# -------------------------
# Normalización
# -------------------------
def _norm(s: str) -> str:
    s = str(s)
    s = "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )
    return s.upper().strip()

def _token_calibre(cal: str) -> str:
    t = _norm(cal).replace(" ", "")
    for suf in ("ACSR", "AAC", "MCM"):
        t = t.replace(suf, "")
    return t

def _aplica_reemplazo(estructura: str, calibre_estructura: str) -> bool:
    e = _norm(estructura)
    if not e.startswith(("A", "TH", "ER", "TM")):
        return False
    t = _token_calibre(calibre_estructura)
    return t not in ("1/0", "1/0AWG")

def _es_conector_yc(material: str) -> bool:
    m = _norm(material)
    # Solo conectores de compresión YC / YPC
    return ("CONECTOR" in m) and ("COMPRESION" in m or "COMPRESIÓN" in m) and bool(re.search(r"\b(YC|YPC)\b", m))

def _tiene_parentesis(material: str) -> bool:
    return bool(re.search(r"\([^)]+\)", _norm(material)))


# -------------------------
# Cargar hoja "conectores"
# -------------------------
def cargar_conectores_mt(archivo_materiales: str) -> pd.DataFrame:
    try:
        df = pd.read_excel(archivo_materiales, sheet_name="conectores")
        df.columns = [str(c).strip() for c in df.columns]

        # Mapeo tolerante
        rename_map = {}
        for col in df.columns:
            c = _norm(col)
            if c.startswith("CALIBRE"):
                rename_map[col] = "Calibre"
            elif c.startswith("COD") or c == "CODIGO":
                rename_map[col] = "Código"
            elif "DESC" in c:
                rename_map[col] = "Descripción"
            elif "APLIC" in c or "ESTRUCT" in c:
                rename_map[col] = "Estructuras aplicables"

        df = df.rename(columns=rename_map)
        for c in ("Calibre", "Código", "Descripción", "Estructuras aplicables"):
            if c not in df.columns:
                df[c] = ""

        return df[["Calibre", "Código", "Descripción", "Estructuras aplicables"]].copy()
    except Exception:
        return pd.DataFrame(columns=["Calibre", "Código", "Descripción", "Estructuras aplicables"])


# -------------------------
# Buscar conector por calibre
# -------------------------
def buscar_conector_mt(calibre: str, tabla_conectores: pd.DataFrame) -> Optional[str]:
    if tabla_conectores is None or getattr(tabla_conectores, "empty", True):
        return None

    tok = _token_calibre(calibre)
    if not tok:
        return None

    # match (X-X) preferido; si no, (X-*)
    pat_sim = re.compile(rf"\(\s*{re.escape(tok)}\s*[-–]\s*{re.escape(tok)}\s*\)")
    pat_any = re.compile(rf"\(\s*{re.escape(tok)}\s*[-–].*?\)")

    candidato = None
    for _, row in tabla_conectores.iterrows():
        desc = str(row.get("Descripción", "") or "")
        d = _norm(desc).replace(" ", "")
        if pat_sim.search(d):
            return desc
        if candidato is None and pat_any.search(d):
            candidato = desc

    return candidato


# -------------------------
# Reemplazar conectores (lista)
# -------------------------
def aplicar_reemplazos_conectores(
    lista_materiales: List[str],
    estructura: str,
    calibre_estructura: str,
    tabla_conectores: pd.DataFrame,
) -> List[str]:

    mats = list(lista_materiales or [])

    # Gate único: si no aplica, devolver tal cual
    if not _aplica_reemplazo(estructura, calibre_estructura):
        return mats

    reemplazo = buscar_conector_mt(calibre_estructura, tabla_conectores)

    out: List[str] = []
    for mat in mats:
        if _es_conector_yc(mat) and (not _tiene_parentesis(mat)) and reemplazo:
            out.append(reemplazo)
        else:
            out.append(mat)
    return out
