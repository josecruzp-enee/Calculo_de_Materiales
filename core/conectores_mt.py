# -*- coding: utf-8 -*-
"""
core/conectores_mt.py
Cargar, seleccionar y reemplazar conectores de compresión según calibre y familia de estructura.
Compatible MT/BT/Neutro. Robusto a tildes, mayúsculas y espacios.
"""

from __future__ import annotations
import re
import unicodedata
import pandas as pd


# ---------- Utilidades de normalización ----------
def _norm(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")  # quita tildes
    return s.strip()

def _norm_up(s: str) -> str:
    return _norm(s).upper()


# ---------- 1) Cargar hoja 'conectores' ----------
def cargar_conectores_mt(archivo_materiales) -> pd.DataFrame:
    """
    Lee hoja 'conectores' y devuelve columnas:
      ['Calibre','Código','Descripción','Estructuras aplicables'].
    Si algo falla, retorna DF vacío con esas columnas.
    """
    try:
        df = pd.read_excel(archivo_materiales, sheet_name="conectores")
    except Exception as e:
        print(f"⚠️ No se pudo cargar hoja 'conectores': {e}")
        return pd.DataFrame(columns=["Calibre", "Código", "Descripción", "Estructuras aplicables"])

    # Normalizar encabezados
    df.columns = [_norm_up(c) for c in df.columns]
    rename = {}
    for c in df.columns:
        c0 = c.lower()
        if "calibre" in c0:      rename[c] = "Calibre"
        elif "codigo" in c0:     rename[c] = "Código"
        elif "descr" in c0:      rename[c] = "Descripción"
        elif "aplic" in c0:      rename[c] = "Estructuras aplicables"
    if rename:
        df = df.rename(columns=rename)

    # Garantizar columnas
    for col in ["Calibre", "Código", "Descripción", "Estructuras aplicables"]:
        if col not in df.columns:
            df[col] = ""

    # Limpieza básica
    df["Calibre"] = df["Calibre"].map(_norm_up)
    df["Código"] = df["Código"].map(_norm_up)
    df["Descripción"] = df["Descripción"].map(lambda x: _norm(x))
    df["Estructuras aplicables"] = df["Estructuras aplicables"].map(_norm_up)

    return df[["Calibre", "Código", "Descripción", "Estructuras aplicables"]]


# ---------- 2) Determinar calibre por familia de estructura ----------
def determinar_calibre_por_estructura(estructura: str, datos_proyecto: dict) -> str:
    """
    Dada la estructura (A-..., B-..., R-..., CT..., etc.) escoge calibre MT/BT/Neutro del proyecto.
    Defaults razonables si no hay dato.
    """
    estructura = _norm_up(estructura)

    calibre_mt = _norm_up(datos_proyecto.get("calibre_mt", ""))
    calibre_bt = _norm_up(datos_proyecto.get("calibre_bt", ""))
    calibre_neu = _norm_up(datos_proyecto.get("calibre_neutro", ""))

    # Familias por prefijo
    if any(estructura.startswith(pref) for pref in ["A", "TM", "TH", "ER"]):
        return calibre_mt or "1/0 ASCR"
    elif any(estructura.startswith(pref) for pref in ["B", "R"]):
        return calibre_bt or "1/0 WP"
    elif any(pref in estructura for pref in ["CT", "N", "NEUTRO"]):
        return calibre_neu or "#2 AWG"
    else:
        return calibre_mt or "1/0 ASCR"


# ---------- 3) Buscar conector simétrico (x-x) y por familia ----------
def _calibre_patron_texto(calibre: str) -> str:
    """
    Normaliza calibre a patrón de texto dentro de paréntesis, sin espacios y sin sufijos (ASCR/AAC/MCM).
    '1/0 ASCR' -> '1/0'
    '266.8 MCM' -> '266.8'
    """
    c = _norm_up(calibre)
    c = c.replace("ASCR", "").replace("AAC", "").replace("MCM", "")
    c = c.replace(" ", "")
    return c.strip()

def _familia(estructura: str) -> str:
    """
    Devuelve familia simplificada para filtrar por 'Estructuras aplicables': A / TM / TH / ER / B / R / CT / N ...
    """
    e = _norm_up(estructura or "")
    if e.startswith("TM"): return "TM"
    if e.startswith("TH"): return "TH"
    if e.startswith("ER"): return "ER"
    if e.startswith("A"):  return "A"
    if e.startswith("B"):  return "B"
    if e.startswith("R"):  return "R"
    if e.startswith("CT"): return "CT"
    if e.startswith("N"):  return "N"
    return "A"  # default: MT

def buscar_conector_mt(
    calibre: str,
    tabla_conectores: pd.DataFrame,
    codigo_estructura: str | None = None
) -> str | None:
    """
    Busca un conector preferentemente simétrico (x-x) y compatible con la familia de la estructura.
    - calibre: '1/0 ASCR', '3/0 ASCR', '266.8 MCM', etc.
    - codigo_estructura: 'A-I-5', 'PC-40', 'R-1' (opcional)
    """
    if tabla_conectores.empty or not calibre:
        return None

    cpat = _calibre_patron_texto(calibre)  # '1/0', '266.8', etc.
    if not cpat:
        return None

    fam = _familia(codigo_estructura)
    # patrón ( 1/0 - 1/0 ) con posibles espacios y guión o en dash
    patron = re.compile(rf"\(\s*{re.escape(cpat)}\s*[-–]\s*{re.escape(cpat)}\s*\)", re.IGNORECASE)

    candidatos = []
    for _, fila in tabla_conectores.iterrows():
        desc_raw = fila.get("Descripción", "")
        desc = _norm_up(desc_raw).replace(" ", "")
        aplica = _norm_up(fila.get("Estructuras aplicables", ""))
        compatible = True
        if aplica:
            familias = [x.strip() for x in aplica.split(",") if x.strip()]
            if familias:
                compatible = fam in familias

        if patron.search(desc) and compatible:
            candidatos.append(str(desc_raw))

    return candidatos[0] if candidatos else None


# ---------- 4) Aplicar reemplazos en lista de materiales ----------
def aplicar_reemplazos_conectores(
    lista_materiales: list[str],
    calibre_estructura: str,
    tabla_conectores: pd.DataFrame,
    codigo_estructura: str | None = None
) -> list[str]:
    """
    Reemplaza entradas que contengan 'CONECTOR' y 'COMPRES' (cubre COMPRESIÓN/COMPRESION)
    por el conector de la tabla que mejor aplica al calibre y familia.
    """
    out = []
    for mat in lista_materiales:
        m_up = _norm_up(mat)
        if "CONECTOR" in m_up and "COMPRES" in m_up:
            nuevo = buscar_conector_mt(
                calibre=calibre_estructura,
                tabla_conectores=tabla_conectores,
                codigo_estructura=codigo_estructura,
            )
            out.append(nuevo if nuevo else mat)
        else:
            out.append(mat)
    return out
