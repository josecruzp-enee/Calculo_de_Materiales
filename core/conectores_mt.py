# -*- coding: utf-8 -*-
"""
core/conectores_mt.py
Utilidades para cargar la hoja de conectores y reemplazar en función del calibre y tipo
de estructura. Tolerante a acentos, mayúsculas/minúsculas y variaciones en la
descripción (“COMPRESION” / “COMPRESIÓN”, espacios, MCM/ASCR/AAC, etc.).

Funciones públicas:
- cargar_conectores_mt(archivo_materiales) -> pd.DataFrame
- determinar_calibre_por_estructura(cod_estructura, datos_proyecto) -> str
- aplicar_reemplazos_conectores(lista_materiales, calibre_estructura, tabla_conectores) -> list[str]
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional, List

import pandas as pd


# =========================
# Normalización de texto
# =========================
def _sin_acentos(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", str(s))
        if unicodedata.category(c) != "Mn"
    )

def _norm(s: str) -> str:
    """Mayúsculas + sin acentos + strip."""
    return _sin_acentos(s).upper().strip()


# =========================
# Carga de hoja "conectores"
# =========================
def cargar_conectores_mt(archivo_materiales: str) -> pd.DataFrame:
    """
    Carga la hoja 'conectores' del Excel de materiales.
    Devuelve siempre un DataFrame con columnas: Calibre, Código, Descripción, Estructuras aplicables
    (crea columnas vacías si faltan).
    """
    try:
        df = pd.read_excel(archivo_materiales, sheet_name="conectores")
        # Normalizar encabezados
        df.columns = [c.strip() for c in df.columns]

        # Mapear nombres esperados (tolerante)
        rename_map = {}
        for col in df.columns:
            col_n = _norm(col)
            if col_n.startswith("CALIBRE"):
                rename_map[col] = "Calibre"
            elif col_n.startswith("COD") or col_n == "CODIGO":
                rename_map[col] = "Código"
            elif "DESC" in col_n:
                rename_map[col] = "Descripción"
            elif "APLIC" in col_n or "ESTRUCT" in col_n:
                rename_map[col] = "Estructuras aplicables"

        df = df.rename(columns=rename_map)

        # Asegurar columnas
        for c in ["Calibre", "Código", "Descripción", "Estructuras aplicables"]:
            if c not in df.columns:
                df[c] = ""

        # Orden amistoso
        return df[["Calibre", "Código", "Descripción", "Estructuras aplicables"]]
    except Exception as e:
        print(f"⚠️ No se pudo cargar hoja 'conectores': {e}")
        return pd.DataFrame(columns=["Calibre", "Código", "Descripción", "Estructuras aplicables"])


# =========================
# Calibre según estructura
# =========================
def determinar_calibre_por_estructura(estructura: str, datos_proyecto: dict) -> str:
    """
    Heurística simple:
    - A*, TM*, TH*, ER*  → calibre MT (por defecto '1/0 ACSR')
    - B*, R*             → calibre BT (por defecto '1/0 WP')
    - contiene CT / N    → calibre Neutro (por defecto '#2 AWG')
    - otro               → calibre MT
    """
    estructura = _norm(estructura)

    calibre_mt = _norm(datos_proyecto.get("calibre_mt", "") or "")
    calibre_bt = _norm(datos_proyecto.get("calibre_bt", "") or "")
    calibre_n  = _norm(datos_proyecto.get("calibre_neutro", "") or "")

    if any(estructura.startswith(pref) for pref in ("A", "TM", "TH", "ER")):
        return calibre_mt or "1/0 ACSR"
    if any(estructura.startswith(pref) for pref in ("B", "R")):
        return calibre_bt or "1/0 WP"
    if ("CT" in estructura) or (estructura.startswith("N")) or ("NEUTRO" in estructura):
        return calibre_n or "#2 AWG"
    return calibre_mt or "1/0 ACSR"


# =========================
# Búsqueda tolerante del conector
# =========================
def _calibre_token(cal: str) -> str:
    """Token para coincidir dentro de paréntesis: sin espacios ni sufijos."""
    return (
        _norm(cal)
        .replace(" ", "")
        .replace("ACSR", "")
        .replace("AAC", "")
        .replace("MCM", "")
        .strip()
    )

def buscar_conector_mt(calibre: str, tabla_conectores: pd.DataFrame) -> Optional[str]:
    """
    Estrategia de matching (por orden):
      1) Simétrico exacto: (X-X) → ej. (266.8-266.8), (1/0-1/0)
      2) Compatible: (X-ALGO)  → ej. (266.8-3/0), (266.8-2/0)
      3) Último recurso: si contiene el token (X) + 'CONECTOR' + 'COMPRESION'
    Devuelve la 'Descripción' del conector o None si no encuentra.
    """
    if tabla_conectores is None or getattr(tabla_conectores, "empty", True):
        return None

    token = _calibre_token(calibre)
    if not token:
        return None

    pat_sim = re.compile(rf"\(\s*{re.escape(token)}\s*[-–]\s*{re.escape(token)}\s*\)")
    pat_any = re.compile(rf"\(\s*{re.escape(token)}\s*[-–].*?\)")

    candidato = None
    for _, row in tabla_conectores.iterrows():
        desc = str(row.get("Descripción", ""))
        desc_nosp = _norm(desc).replace(" ", "")

        # 1) simétrico
        if pat_sim.search(desc_nosp):
            return desc

        # 2) compatible
        if candidato is None and pat_any.search(desc_nosp):
            candidato = desc

        # 3) último recurso
        if candidato is None and (token in desc_nosp) and ("CONECTOR" in desc_nosp) and ("COMPRESION" in desc_nosp):
            candidato = desc

    return candidato


# =========================
# Reemplazo en lista de materiales
# =========================
def _es_conector(material: str) -> bool:
    m = _norm(material)
    return ("CONECTOR" in m) and (("COMPRESION" in m) or ("COMPRESIÓN" in m))

def aplicar_reemplazos_conectores(
    lista_materiales: List[str],
    calibre_estructura: str,
    tabla_conectores: pd.DataFrame,
) -> List[str]:
    """
    Recorre la lista de materiales y reemplaza los que sean conectores por
    el que corresponda al calibre de ESTA estructura.
    """
    salida: List[str] = []
    for mat in (lista_materiales or []):
        if _es_conector(mat):
            nuevo = buscar_conector_mt(calibre_estructura, tabla_conectores)
            salida.append(nuevo if nuevo else mat)
        else:
            salida.append(mat)
    return salida

