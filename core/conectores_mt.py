# -*- coding: utf-8 -*-
"""
core/conectores_mt.py
Carga y reemplazo de conectores de compresión según calibre y tipo de estructura.
"""

from __future__ import annotations
import re
import unicodedata
import pandas as pd

# --------------------------
# Utilidades de normalización
# --------------------------
def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def _norm_txt(s: str) -> str:
    s = str(s or "")
    s = _strip_accents(s)
    s = s.replace("º", "").replace("°", "")
    return s.upper().strip()

# --------------------------
# 1) Cargar hoja 'conectores'
# --------------------------
def cargar_conectores_mt(archivo_materiales) -> pd.DataFrame:
    """Devuelve columnas: Calibre, Código, Descripción, Estructuras aplicables."""
    try:
        df = pd.read_excel(archivo_materiales, sheet_name="conectores")
    except Exception:
        return pd.DataFrame(columns=["Calibre", "Código", "Descripción", "Estructuras aplicables"])

    # Normaliza encabezados
    df.columns = [_norm_txt(c).title() for c in df.columns]
    if "Descripción" not in df.columns:
        for col in df.columns:
            if "DESC" in _norm_txt(col):
                df = df.rename(columns={col: "Descripción"})
                break

    # Asegura columnas esperadas
    for col in ["Calibre", "Código", "Descripción", "Estructuras aplicables"]:
        if col not in df.columns:
            df[col] = ""

    # Normaliza valores de texto (mantiene capitalización original en Descripción para el PDF)
    df["Calibre"] = df["Calibre"].apply(_norm_txt)
    df["Código"] = df["Código"].apply(_norm_txt)
    df["Estructuras aplicables"] = df["Estructuras aplicables"].apply(_norm_txt)

    return df[["Calibre", "Código", "Descripción", "Estructuras aplicables"]]

# -------------------------------------------------
# 2) Determinar calibre por tipo de estructura (A/B)
# -------------------------------------------------
def determinar_calibre_por_estructura(codigo_estructura: str, datos_proyecto: dict) -> str:
    """
    A*, TM*, TH*, ER*   → MT
    B*, R*              → BT
    CT*, *N*, *NEUTRO*  → Neutro
    """
    e = _norm_txt(codigo_estructura)
    cal_mt = _norm_txt(datos_proyecto.get("calibre_mt", "")) or "1/0 ASCR"
    cal_bt = _norm_txt(datos_proyecto.get("calibre_bt", "")) or "1/0 WP"
    cal_n  = _norm_txt(datos_proyecto.get("calibre_neutro", "")) or "#2 AWG"

    if e.startswith(("A", "TM", "TH", "ER")):
        return cal_mt
    if e.startswith(("B", "R")):
        return cal_bt
    if (" CT" in f" {e} ") or (" N" in f" {e} ") or ("NEUTRO" in e):
        return cal_n
    return cal_mt

# -------------------------------------------------
# 3) Buscar conector simétrico o compatible
# -------------------------------------------------
def _pat_simetrico(calibre_norm: str) -> re.Pattern:
    # (1/0-1/0)  (266.8-266.8) etc.
    return re.compile(rf"\(\s*{re.escape(calibre_norm)}\s*[-–]\s*{re.escape(calibre_norm)}\s*\)", re.IGNORECASE)

def _pat_compatible(calibre_norm: str) -> re.Pattern:
    # (266.8-3/0), (266.8-2/0), ... — busca al menos que aparezca calibre_norm dentro del paréntesis
    return re.compile(rf"\(\s*{re.escape(calibre_norm)}\s*[-–].*?\)", re.IGNORECASE)

def buscar_conector_mt(calibre: str, tabla_conectores: pd.DataFrame) -> str | None:
    """
    1) Intenta simétrico (calibre-calibre)
    2) Si no hay, intenta compatible (calibre-otro)
    """
    if tabla_conectores is None or tabla_conectores.empty:
        return None

    cal = _norm_txt(calibre)
    # El calibre en conectores suele venir con o sin sufijo (ASCR, MCM). Quitamos eso para el patrón.
    cal_norm = cal.replace(" ", "")
    cal_norm = cal_norm.replace("ASCR", "").replace("AAC", "").replace("MCM", "").strip()

    # Recorre por orden
    for patron in (_pat_simetrico(cal_norm), _pat_compatible(cal_norm)):
        for _, fila in tabla_conectores.iterrows():
            desc_raw = str(fila.get("Descripción", ""))
            desc = _norm_txt(desc_raw).replace(" ", "")
            if patron.search(desc):
                return desc_raw  # devolvemos tal cual para que salga bonito en PDF
    return None

# -------------------------------------------------
# 4) Reemplazo dentro de la lista de materiales
# -------------------------------------------------
def aplicar_reemplazos_conectores(
    lista_materiales: list[str],
    calibre_estructura: str,
    tabla_conectores: pd.DataFrame,
    logger=None,
) -> list[str]:
    """
    Reemplaza cualquier ítem que contenga 'CONECTOR' y 'COMPRESION/COMPRESIÓN'
    por el conector que corresponda al calibre de la estructura.
    """
    if not lista_materiales:
        return lista_materiales

    out = []
    cal = calibre_estructura
    for mat in lista_materiales:
        mat_norm = _norm_txt(mat)
        if ("CONECTOR" in mat_norm) and (("COMPRESION" in mat_norm) or ("COMPRESION" in mat_norm.replace("Ó","O"))):
            nuevo = buscar_conector_mt(cal, tabla_conectores)
            if nuevo:
                if logger: logger(f"🔁 Reemplazo: '{mat}'  →  '{nuevo}'")
                out.append(nuevo)
                continue
        out.append(mat)
    return out
