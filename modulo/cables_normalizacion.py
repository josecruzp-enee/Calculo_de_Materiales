# -*- coding: utf-8 -*-
"""
cables_normalizacion.py
Normalización de texto/llaves (tildes, espacios, mayúsculas) y helpers.
"""

from __future__ import annotations
import re


def _norm_txt(s: str) -> str:
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s)).strip()


def _norm_key(s: str) -> str:
    # Llave normalizada para buscar en diccionarios
    return _norm_txt(s).upper()


def _unidad_norm(u: str) -> str:
    return _norm_key(u)


def conductores_de(tipo: str) -> str:
    # Si vos calculabas conductores según tipo/config, mantenelo aquí.
    # Como fallback, devolvemos el tipo.
    return _norm_key(tipo)


def calibre_corto_desde_seleccion(calibre: str) -> str:
    """
    Convierte selecciones tipo "1/0 ACSR" -> "1/0"
    o "266.8 MCM" -> "266.8 MCM"
    o "2 WP" -> "2 WP" (según tu criterio).
    """
    s = _norm_txt(calibre)
    if not s:
        return ""
    parts = s.split()
    # regla simple: devolver primeros 1-2 tokens si es MCM
    if "MCM" in s.upper():
        return s.upper()
    return parts[0].upper()
