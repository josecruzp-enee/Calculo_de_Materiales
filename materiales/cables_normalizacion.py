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


def conductores_de(tipo: str, cfg: str) -> int:
    """
    Devuelve el número de conductores según Tipo y Configuración.
    (igual a tu script original)
    """
    t = _norm_key(tipo)
    c = _norm_key(cfg)

    if not c:
        return 0

    if t == "MT":
        if c == "1F": return 1
        if c == "2F": return 2
        if c == "3F": return 3
        return 0

    if t == "BT":
        if c == "1F": return 1
        if c == "2F": return 2
        return 0

    if t == "N":
        return 1 if c == "N" else 0

    if t == "HP":
        if c == "1F": return 1
        if c == "2F": return 2
        return 0

    # soporta "RETENIDA" y "RETENIDA" con tilde en ÚNICA / sin tilde
    if t in ("RETENIDA", "RETENIDA "):
        return 1 if c in ("ÚNICA", "UNICA") else 0

    # también soportar si alguien manda "RETENIDA" como "RETENIDA" o "Retenida"
    if t == "RETENIDA":
        return 1 if c in ("ÚNICA", "UNICA") else 0

    return 0

def calibre_corto_desde_seleccion(tipo: str, calibre: str) -> str:
    """
    Compatibilidad con cables_logica.py: acepta (tipo, calibre_o_desc).

    Convierte selecciones tipo:
    - "1/0 ACSR" -> "1/0 ACSR"
    - "266.8 MCM" -> "266.8 MCM"
    - "2 WP" -> "2 WP"
    """
    s = _norm_txt(calibre)
    if not s:
        return ""

    parts = s.split()

    # Si es MCM, devolver completo en mayúsculas
    if "MCM" in s.upper():
        return s.upper()

    # Si trae 2 tokens (ej: "1/0 ACSR", "2 WP"), devolver ambos
    if len(parts) >= 2:
        return f"{parts[0].upper()} {parts[1].upper()}"

    # Si solo trae 1 token, devolver ese
    return parts[0].upper()

