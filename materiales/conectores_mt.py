# -*- coding: utf-8 -*-
"""
materiales/conectores_mt.py

Regla:
- En MT (estructuras A/TH/ER/TM), el ÚNICO conector que puede reemplazarse es:
    YC 25A25 (1/0-1/0)
- Si calibre_mt_global == 1/0 => NO reemplazar nada.
- Si calibre_mt_global != 1/0 => reemplazar SOLO ese YC 25A25 por el conector
  correspondiente al calibre_mt_global desde la hoja 'conectores'.

Casos:
- 1/0 ACSR  -> YC 25A25 (sin cambio)
- 3/0 ACSR  -> YC 28A28 (3/0-3/0)
- 266.8 MCM -> YPC 33R33R (266.8-266.8)
- 477 MCM   -> YHN-525 (4/0-477)

NO toca:
- YC 28A25, YC 28A28 existentes, bimetálicos, YG, pines, etc.
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
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    return s.upper().strip()


def _token_calibre(cal: str) -> str:
    """
    Extrae:
      "1/0" -> "1/0"
      "3/0 AWG" -> "3/0"
      "Cable ... 266.8 MCM" -> "266.8"
      "Cable ... 477 MCM" -> "477"
    """
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

    t = s.replace(" ", "")
    for suf in ("ACSR", "AAC", "MCM", "AWG"):
        t = t.replace(suf, "")
    return t.strip()


def _es_1_0(calibre_mt: str) -> bool:
    return _token_calibre(calibre_mt) == "1/0"


def _es_estructura_mt(estructura: str) -> bool:
    return _norm(estructura).startswith(("A", "TH", "ER", "TM"))


# -------------------------
# Cargar hoja "conectores"
# -------------------------
def cargar_conectores_mt(archivo_materiales: str) -> pd.DataFrame:
    try:
        df = pd.read_excel(archivo_materiales, sheet_name="conectores")
        df.columns = [str(c).strip() for c in df.columns]

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

        return df[["Calibre", "Código", "Descripción",
                   "Estructuras aplicables"]].copy()

    except Exception:
        return pd.DataFrame(columns=[
            "Calibre", "Código", "Descripción", "Estructuras aplicables"
        ])


# -------------------------
# Caso específico 477 MCM
# -------------------------
def _buscar_conector_477(tabla_conectores: pd.DataFrame) -> Optional[str]:
    """
    Para 477 MCM busca específicamente:
      Calibre = 477 MCM
      Código  = YHN-525
    """
    for _, row in tabla_conectores.iterrows():
        calibre = _token_calibre(str(row.get("Calibre", "") or ""))
        codigo = _norm(str(row.get("Código", "") or ""))
        desc = str(row.get("Descripción", "") or "").strip()

        if calibre == "477" and codigo == "YHN-525" and desc:
            return desc

    return None


# -------------------------
# Buscar conector por calibre MT global
# -------------------------
def buscar_conector_por_calibre(
    calibre_mt: str,
    tabla_conectores: pd.DataFrame
) -> Optional[str]:
    """
    Preferencia general:
      1) (X-X)
      2) (X-*)

    Caso específico:
      477 MCM -> YHN-525
    """
    if tabla_conectores is None or getattr(tabla_conectores, "empty", True):
        return None

    tok = _token_calibre(calibre_mt)
    if not tok:
        return None

    # Caso ENEE 477 MCM
    if tok == "477":
        return _buscar_conector_477(tabla_conectores)

    # Lógica original para 3/0, 266.8, etc.
    pat_sim = re.compile(
        rf"\(\s*{re.escape(tok)}\s*[-–]\s*{re.escape(tok)}\s*\)"
    )
    pat_any = re.compile(
        rf"\(\s*{re.escape(tok)}\s*[-–].*?\)"
    )

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
# Reemplazo específico: SOLO YC 25A25
# -------------------------
def reemplazar_solo_yc25a25_mt(
    lista_materiales: List[str],
    estructura: str,
    calibre_mt_global: str,
    tabla_conectores: pd.DataFrame,
) -> List[str]:
    """
    Reemplaza SOLO:
      YC 25A25 (1/0-1/0)

    No modifica ningún otro conector.
    """
    mats = list(lista_materiales or [])

    # Solo estructuras MT y solo cuando el calibre sea distinto de 1/0
    if not _es_estructura_mt(estructura) or _es_1_0(calibre_mt_global):
        return mats

    reemplazo = buscar_conector_por_calibre(
        calibre_mt_global, tabla_conectores
    )

    if not reemplazo:
        return mats

    # Detectar exclusivamente YC 25A25 (1/0-1/0)
    pat_yc25 = re.compile(r"\bYC\b.*\b25A25\b")
    pat_10_10 = re.compile(r"\(\s*1/0\s*[-–]\s*1/0\s*\)")

    out: List[str] = []

    for mat in mats:
        m = _norm(mat)

        if pat_yc25.search(m) and pat_10_10.search(m):
            out.append(reemplazo)
        else:
            out.append(mat)

    return out
