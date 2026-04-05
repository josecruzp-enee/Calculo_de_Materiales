# -*- coding: utf-8 -*-
"""
leer_tabla.py
Convierte texto pegado (desde Excel) en DataFrame.
"""

from __future__ import annotations
import pandas as pd
import io


def leer_tabla(texto: str) -> pd.DataFrame:
    """
    Convierte texto pegado desde Excel en DataFrame.

    Soporta:
    - Tabulaciones (\t) → Excel típico
    - Espacios múltiples

    Retorna DataFrame limpio o vacío si falla.
    """

    if not texto or not texto.strip():
        return pd.DataFrame()

    # -------------------------
    # Intento 1: formato Excel (tabs)
    # -------------------------
    try:
        df = pd.read_csv(io.StringIO(texto), sep="\t")
        if df.shape[1] > 1:
            return df
    except Exception:
        pass

    # -------------------------
    # Intento 2: espacios múltiples
    # -------------------------
    try:
        df = pd.read_csv(io.StringIO(texto), sep=r"\s{2,}", engine="python")
        if df.shape[1] > 1:
            return df
    except Exception:
        pass

    # -------------------------
    # Fallback
    # -------------------------
    return pd.DataFrame()
