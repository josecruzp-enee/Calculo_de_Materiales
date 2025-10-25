# -*- coding: utf-8 -*-
"""
conectores_mt.py
Módulo para cargar, buscar y reemplazar conectores de compresión según calibre y tipo de estructura.
Compatible con niveles: Primario (MT), Secundario (BT) y Neutro.
"""
from __future__ import annotations

import re
import unicodedata
import pandas as pd


# ---------- util: normalizar (sin tildes, mayúsculas) ----------
def _norm(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")  # quita tildes
    return s.upper()


# === 1️⃣ Cargar hoja de conectores ===
def cargar_conectores_mt(archivo_materiales):
    """Carga la hoja 'conectores' desde Estructura_datos.xlsx."""
    try:
        df = pd.read_excel(archivo_materiales, sheet_name="conectores")
        df.columns = [c.strip().capitalize() for c in df.columns]

        if "Descripción" not in df.columns:
            for col in df.columns:
                if "desc" in col.lower():
                    df = df.rename(columns={col: "Descripción"})

        columnas_esperadas = ["Calibre", "Código", "Descripción", "Estructuras aplicables"]
        for col in columnas_esperadas:
            if col not in df.columns:
                df[col] = ""

        return df[columnas_esperadas]
    except Exception as e:
        print(f"⚠️ No se pudo cargar hoja 'conectores': {e}")
        return pd.DataFrame(columns=["Calibre", "Código", "Descripción", "Estructuras aplicables"])


# === 2️⃣ Determinar calibre según tipo de estructura ===
def determinar_calibre_por_estructura(estructura, datos_proyecto):
    """
    Devuelve el calibre apropiado según el tipo de estructura (MT, BT o Neutro).
    """
    estructura = _norm(estructura).strip()

    calibre_mt = _norm(datos_proyecto.get("calibre_mt", "")).strip()
    calibre_bt = _norm(datos_proyecto.get("calibre_bt", "")).strip()
    calibre_neutro = _norm(datos_proyecto.get("calibre_neutro", "")).strip()

    # Clasificación por prefijo o coincidencia
    if any(estructura.startswith(pref) for pref in ["A", "TM", "TH", "ER"]):
        return calibre_mt or "1/0 ASCR"
    elif any(estructura.startswith(pref) for pref in ["B", "R"]):
        return calibre_bt or "1/0 WP"
    elif any(pref in estructura for pref in ["CT", " N", "NEUTRO"]):
        return calibre_neutro or "#2 AWG"
    else:
        return calibre_mt or "1/0 ASCR"


# === 3️⃣ Buscar conector adecuado según calibre ===
def buscar_conector_mt(calibre, tabla_conectores: pd.DataFrame):
    """
    Busca un conector simétrico (mismo calibre en ambos extremos).
      - 1/0 ASCR → (1/0-1/0)
      - 3/0 ASCR → (3/0-3/0)
      - 266.8 MCM → (266.8-266.8)
    """
    if tabla_conectores.empty or not calibre:
        return None

    # Normalizar calibre: quitar espacios y sufijos de material
    cal = _norm(calibre)
    cal = cal.replace("ASCR", "").replace("AAC", "").replace("MCM", "").strip()
    cal = cal.replace(" ", "")

    patron = re.compile(rf"\(\s*{re.escape(cal)}\s*[-–]\s*{re.escape(cal)}\s*\)", re.IGNORECASE)

    for _, fila in tabla_conectores.iterrows():
        desc_norm = _norm(fila.get("Descripción", "")).replace(" ", "")
        if patron.search(desc_norm):
            return str(fila.get("Descripción", "")).strip()

    return None


# === 4️⃣ Aplicar reemplazo de conectores ===
def aplicar_reemplazos_conectores(lista_materiales, calibre_estructura, tabla_conectores: pd.DataFrame):
    """
    Reemplaza materiales tipo 'CONECTOR DE COMPRESION/COMPRESIÓN' por el adecuado según calibre de esa estructura.
    Insensible a tildes y mayúsculas.
    """
    materiales_modificados = []
    for mat in lista_materiales:
        txt = str(mat)
        nrm = _norm(txt)
        if "CONECTOR" in nrm and "COMPRESION" in nrm:  # cubre COMPRESIÓN/COMPRESION
            nuevo_con = buscar_conector_mt(calibre_estructura, tabla_conectores)
            if nuevo_con:
                materiales_modificados.append(nuevo_con)
                continue
        materiales_modificados.append(txt)
    return materiales_modificados
