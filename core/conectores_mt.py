# -*- coding: utf-8 -*-
"""
core/conectores_mt.py

Cargar, buscar y reemplazar conectores de compresión según calibre y tipo de estructura.
- Tolerante a tildes (COMPRESIÓN / COMPRESION) y mayúsculas/minúsculas.
- Match robusto para calibres simétricos: 1/0 -> (1/0-1/0), 3/0 -> (3/0-3/0), 266.8 -> (266.8-266.8).
- Opcional: si existe la columna 'Estructuras aplicables', puede filtrarse por familia (A, TM, TH, ER, etc.).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional, Sequence

import pandas as pd


# ============================================================================
# Utils
# ============================================================================

def _nrm(s: str) -> str:
    """
    Normaliza cadenas:
    - quita tildes,
    - aplana espacios,
    - convierte a MAYÚSCULAS.
    """
    s = str(s or "")
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))  # sin tildes
    return re.sub(r"\s+", " ", s).strip().upper()


def _familia_estructura(codigo: str) -> str:
    """
    Intenta derivar una 'familia' simple desde el código de estructura.
    Ej.: 'A-I-4' -> 'A', 'B-II-1' -> 'B', 'PC-40' -> 'PC', 'R-1' -> 'R', 'CT-N' -> 'CT'
    """
    c = _nrm(codigo)
    # tomamos el primer segmento al encontrar separadores comunes
    for sep in ("-", " "):
        if sep in c:
            return c.split(sep, 1)[0]
    return c


def _normaliza_calibre(calibre: str) -> str:
    """
    Normaliza el calibre removiendo sufijos de material y espacios.
    Ej.: '1/0 ASCR' -> '1/0' ; '266.8 MCM' -> '266.8'
    """
    c = _nrm(calibre).replace(" ", "")
    for suf in ("ASCR", "AAC", "MCM", "AWG", "WP"):
        c = c.replace(suf, "")
    return c.strip()


# ============================================================================
# Carga de hoja de conectores
# ============================================================================

def cargar_conectores_mt(archivo_materiales: str) -> pd.DataFrame:
    """
    Carga la hoja 'conectores' desde el Excel de materiales.
    Devuelve un DataFrame con columnas estándar:
      ['Calibre', 'Código', 'Descripción', 'Estructuras aplicables']
    (las que no existan se crean vacías).
    """
    try:
        df = pd.read_excel(archivo_materiales, sheet_name="conectores")

        # Normalizar encabezados
        cols = {_nrm(c): c for c in df.columns}
        # mapeos flexibles
        map_flex = {
            "CALIBRE": "Calibre",
            "CODIGO": "Código",
            "CÓDIGO": "Código",
            "DESCRIPCION": "Descripción",
            "DESCRIPCIÓN": "Descripción",
            "ESTRUCTURAS APLICABLES": "Estructuras aplicables",
        }

        df = df.rename(columns={orig: map_flex.get(_nrm(orig), orig) for orig in df.columns})

        for col in ("Calibre", "Código", "Descripción", "Estructuras aplicables"):
            if col not in df.columns:
                df[col] = ""

        # recortar y asegurar tipos string
        for col in ("Calibre", "Código", "Descripción", "Estructuras aplicables"):
            df[col] = df[col].astype(str)

        return df[["Calibre", "Código", "Descripción", "Estructuras aplicables"]]

    except Exception as e:
        print(f"⚠️ No se pudo cargar hoja 'conectores': {e}")
        return pd.DataFrame(columns=["Calibre", "Código", "Descripción", "Estructuras aplicables"])


# ============================================================================
# Calibres por tipo de estructura
# ============================================================================

def determinar_calibre_por_estructura(estructura: str, datos_proyecto: dict) -> str:
    """
    Devuelve el calibre apropiado según el tipo de estructura (MT, BT o Neutro).
    Heurística por prefijo del código de estructura.
    """
    estructura = (estructura or "").strip().upper()

    calibre_mt = str(datos_proyecto.get("calibre_mt", "")).strip() or "1/0 ASCR"
    calibre_bt = str(datos_proyecto.get("calibre_bt", "")).strip() or "1/0 WP"
    calibre_n  = str(datos_proyecto.get("calibre_neutro", "")).strip() or "#2 AWG"

    if estructura.startswith(("A", "TM", "TH", "ER", "PC")):
        return calibre_mt
    if estructura.startswith(("B", "R")):
        return calibre_bt
    if any(p in estructura for p in ("CT", "N", "NEUTRO")):
        return calibre_n
    return calibre_mt


# ============================================================================
# Búsqueda del conector adecuado
# ============================================================================

def _coincide_familia(fila_aplicables: str, familia: str) -> bool:
    """
    Si la celda 'Estructuras aplicables' existe, valida que contenga la familia.
    Es tolerante a tildes, espacios y comas.
    Si la celda viene vacía, no restringe.
    """
    if not fila_aplicables:
        return True
    lista = [_nrm(x) for x in re.split(r"[;,/| ]+", fila_aplicables) if x.strip()]
    return _nrm(familia) in lista


def buscar_conector_mt(
    calibre: str,
    tabla_conectores: pd.DataFrame,
    familia_estructura: Optional[str] = None,
) -> Optional[str]:
    """
    Busca un conector SIMÉTRICO para el calibre dado.
    - calibre: ej. '1/0 ASCR' o '266.8 MCM'
    - familia_estructura: ej. 'A', 'B', 'PC' (opcional; se filtra si hay columna 'Estructuras aplicables')
    Devuelve la 'Descripción' original del Excel si encuentra match, o None si no hay.
    """
    if tabla_conectores.empty or not calibre:
        return None

    cn = _normaliza_calibre(calibre)            # '1/0 ASCR' -> '1/0'
    patron = re.compile(rf"\(\s*{re.escape(cn)}\s*[-–]\s*{re.escape(cn)}\s*\)", re.IGNORECASE)

    col_desc = "Descripción" if "Descripción" in tabla_conectores.columns else "Descripcion"

    for _, fila in tabla_conectores.iterrows():
        desc_nrm = _nrm(fila.get(col_desc, "")).replace(" ", "")
        if patron.search(desc_nrm):
            # Si pide familia y hay columna de aplicables, validamos
            aplicables = fila.get("Estructuras aplicables", "")
            if familia_estructura and not _coincide_familia(aplicables, familia_estructura):
                continue
            return fila.get(col_desc)

    return None


# ============================================================================
# Reemplazo en la lista de materiales
# ============================================================================

def aplicar_reemplazos_conectores(
    lista_materiales: Sequence[str],
    calibre_estructura: str,
    tabla_conectores: pd.DataFrame,
    codigo_estructura: Optional[str] = None,
) -> list[str]:
    """
    Recorre los materiales de UNA estructura y reemplaza los “conectores de compresión”
    por el conector correcto para el calibre de ESA estructura.

    - Detecta conectores de manera robusta: “CONECTOR … COMPRESION/COMPRESIÓN …”
    - Intenta match SIMÉTRICO (1/0-1/0, 266.8-266.8, etc.)
    - Si hay columna 'Estructuras aplicables' y se suministra `codigo_estructura`,
      se filtra por familia ('A', 'B', 'PC', 'R', 'CT', etc.).
    """
    familia = _familia_estructura(codigo_estructura) if codigo_estructura else None

    salida: list[str] = []
    for mat in lista_materiales:
        texto = _nrm(mat)
        # tolerante a tildes: COMPRESION/COMPRESIÓN => _nrm los unifica
        if "CONECTOR" in texto and "COMPRESION" in texto:
            nuevo = buscar_conector_mt(calibre_estructura, tabla_conectores, familia_estructura=familia)
            if nuevo:
                salida.append(nuevo)
                continue  # no agregamos el original
        salida.append(mat)

    return salida
