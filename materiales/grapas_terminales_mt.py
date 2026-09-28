# -*- coding: utf-8 -*-
"""
materiales/grapas_terminales_mt.py

Regla:
- Las grapas terminales cambian según el calibre MT global.
- 1/0 y 3/0 utilizan las grapas base.
- 266.8 y 477 utilizan las grapas de mayor rango.

Escuadra:
- 1/0, 3/0   -> ANDERSON SD-57-C  (2 - 4/0)
- 266.8, 477 -> ANDERSON SD-86-C  (3/0 - 556)

Recta:
- 1/0, 3/0   -> ANDERSON MDE-60-C     (1/0 - 4/0)
- 266.8, 477 -> ANDERSON 87682-2000   (266.8 - 556 MCM)

NO modifica:
- Grapa terminal tipo recto para cable de guarda Ø=1/4"
  ANDERSON MDE-46-C
"""

from __future__ import annotations
import re
import unicodedata
from typing import List


def _norm(s: str) -> str:
    s = str(s or "")
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    return s.upper().strip()


def _token_calibre(cal: str) -> str:
    s = _norm(cal)

    m = re.search(r"(?<!\d)(1/0|3/0)(?!\d)", s)
    if m:
        return m.group(1)

    if re.search(r"(?<!\d)266\.8(?!\d)", s):
        return "266.8"

    if re.search(r"(?<!\d)477(?:\.0)?(?!\d)", s):
        return "477"

    return ""

def _es_estructura_mt(estructura: str) -> bool:
    s = _norm(estructura)
    return s.startswith(("A", "TH", "ER", "TM")) or s == "MT"


GRAPAS_ESCUADRA = {
    "1/0": "Grapa Terminal tipo Escuadra para Conductor (2 - 4/0)",
    "3/0": "Grapa Terminal tipo Escuadra para Conductor (2 - 4/0)",
    "266.8": "Grapa Terminal tipo Escuadra para Conductor (3/0 - 556)",
    "477": "Grapa Terminal tipo Escuadra para Conductor (3/0 - 556)",
}

GRAPAS_RECTAS = {
    "1/0": "Grapa Terminal tipo Recto para Conductor (1/0 - 4/0)",
    "3/0": "Grapa Terminal tipo Recto para Conductor (1/0 - 4/0)",
    "266.8": "Grapa Terminal tipo Recto para Conductor (266.8 - 556 MCM)",
    "477": "Grapa Terminal tipo Recto para Conductor (266.8 - 556 MCM)",
}


def _es_grapa_escuadra_base(material: str) -> bool:
    m = _norm(material)
    return (
        "GRAPA TERMINAL" in m
        and "ESCUADRA" in m
        and "CONDUCTOR" in m
        and ("SD-57-C" in m or "(2 - 4/0)" in m or "(2-4/0)" in m)
    )


def _es_grapa_recta_base(material: str) -> bool:
    m = _norm(material)

    # Nunca tocar cable de guarda
    if "CABLE DE GUARDA" in m or "MDE-46-C" in m:
        return False

    return (
        "GRAPA TERMINAL" in m
        and "RECTO" in m
        and "CONDUCTOR" in m
        and ("MDE-60-C" in m or "(1/0 - 4/0)" in m or "(1/0-4/0)" in m)
    )


def reemplazar_grapas_terminales_mt(
    lista_materiales: List[str],
    estructura: str,
    calibre_mt_global: str,
) -> List[str]:

    mats = list(lista_materiales or [])

    if not _es_estructura_mt(estructura):
        return mats

    tok = _token_calibre(calibre_mt_global)

    # Para 1/0 y 3/0 las grapas base ya son correctas
    if tok in ("1/0", "3/0"):
        return mats

    if tok not in ("266.8", "477"):
        return mats

    escuadra = GRAPAS_ESCUADRA[tok]
    recta = GRAPAS_RECTAS[tok]

    out: List[str] = []

    for mat in mats:
        if _es_grapa_escuadra_base(mat):
            out.append(escuadra)
        elif _es_grapa_recta_base(mat):
            out.append(recta)
        else:
            out.append(mat)

    return out
