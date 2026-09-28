# -*- coding: utf-8 -*-
"""
materiales/varillas_armar_mt.py

Regla:
- La estructura base utiliza varilla de armar para ACSR # 1/0 AWG.
- Si el calibre MT global cambia, se reemplaza SOLO esa varilla base.
- Si el calibre MT global es 1/0, no se modifica nada.

Correspondencias:
- 1/0 ACSR  -> MG-0135/MG-0318
- 3/0 ACSR  -> MG-0139/MG-0322
- 266.8 MCM -> MG-0144/MG-0327
- 477 MCM   -> MG-0150/MG-0333
"""

from __future__ import annotations
import re
import unicodedata
from typing import List, Optional


# -------------------------
# Normalización
# -------------------------
def _norm(s: str) -> str:
    s = str(s or "")
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    return s.upper().strip()


def _token_calibre(cal: str) -> str:
    """Extrae 1/0, 3/0, 266.8, 477, etc."""
    s = _norm(cal)

    m = re.search(r"(\d+(?:\.\d+)?)\s*MCM", s)
    if m:
        return m.group(1)

    m = re.search(r"#\s*([0-9]+\/0|[0-9]+)", s)
    if m:
        return m.group(1)

    m = re.search(r"\b([0-9]+\/0|[0-9]+)\s*AWG\b", s)
    if m:
        return m.group(1)

    return ""


def _es_estructura_mt(estructura: str) -> bool:
    return _norm(estructura).startswith(("A", "TH", "ER", "TM")) or _norm(estructura) == "MT"


# -------------------------
# Varillas por calibre
# -------------------------
VARILLAS_MT = {
    "1/0": "Varilla de Armar Preformado para Cable ASCR # 1/0 AWG",
    "3/0": "Varilla de Armar Preformado para Cable ASCR # 3/0 AWG",
    "266.8": "Varilla de Armar Preformado para Cable ASCR 266.8 MCM",
    "477": "Varilla de Armar Preformado para Cable AAC 477 / 556 MCM",
}


def buscar_varilla_por_calibre(calibre_mt: str) -> Optional[str]:
    """Devuelve la varilla correspondiente al calibre MT global."""
    tok = _token_calibre(calibre_mt)
    return VARILLAS_MT.get(tok)


# -------------------------
# Detectar varilla base 1/0
# -------------------------
def _es_varilla_base_1_0(material: str) -> bool:
    m = _norm(material)

    return (
        "VARILLA" in m
        and "ARMAR" in m
        and ("ACSR" in m or "ASCR" in m)
        and re.search(r"#\s*1/0\b", m) is not None
    )


# -------------------------
# Reemplazo
# -------------------------
def reemplazar_varilla_armar_mt(
    lista_materiales: List[str],
    estructura: str,
    calibre_mt_global: str,
) -> List[str]:
    """
    Reemplaza SOLO la varilla de armar base de 1/0
    según el calibre MT global.
    """
    mats = list(lista_materiales or [])

    if not _es_estructura_mt(estructura):
        return mats

    tok = _token_calibre(calibre_mt_global)

    # 1/0 es la condición base
    if tok == "1/0":
        return mats

    reemplazo = buscar_varilla_por_calibre(calibre_mt_global)

    # Calibre no definido: no tocar nada
    if not reemplazo:
        return mats

    out: List[str] = []

    for mat in mats:
        if _es_varilla_base_1_0(mat):
            out.append(reemplazo)
        else:
            out.append(mat)

    return out
