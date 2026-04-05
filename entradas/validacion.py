# -*- coding: utf-8 -*-
"""
validar.py

Validación de estructuras contra catálogo ENEE.
"""

import pandas as pd


# =========================================================
# VALIDACIÓN PRINCIPAL
# =========================================================

def validar_estructuras(df: pd.DataFrame, df_indice: pd.DataFrame, log):
    """
    Valida estructuras contra catálogo.

    Retorna:
        errores (list)
        warnings (list)
    """

    errores = []
    warnings = []

    if df is None or df.empty:
        raise ValueError("No hay estructuras para validar")

    if df_indice is None or df_indice.empty:
        warnings.append("⚠️ Índice de estructuras vacío (no se validó contra catálogo)")
        return errores, warnings

    # -------------------------
    # NORMALIZAR
    # -------------------------
    codigos_catalogo = set(
        df_indice["codigodeestructura"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    codigos_df = set(
        df["codigodeestructura"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # -------------------------
    # DETECTAR NO ENCONTRADOS
    # -------------------------
    no_encontrados = codigos_df - codigos_catalogo

    for cod in sorted(no_encontrados):

        sugerencia = _sugerir_codigo(cod, codigos_catalogo)

        if sugerencia:
            warnings.append(f"⚠️ {cod} no existe. ¿Quisiste decir {sugerencia}?")
        else:
            errores.append(f"❌ {cod} no existe en catálogo")

    # -------------------------
    # LOG
    # -------------------------
    if errores:
        log("❌ ERRORES:")
        for e in errores:
            log(e)

    if warnings:
        log("⚠️ WARNINGS:")
        for w in warnings:
            log(w)

    return errores, warnings


# =========================================================
# SUGERENCIAS (TIPO CORRECCIÓN AUTOMÁTICA)
# =========================================================

def _sugerir_codigo(codigo, catalogo):

    codigo = str(codigo).upper()

    # búsqueda simple por parecido
    for c in catalogo:
        if _distancia_simple(codigo, c) <= 2:
            return c

    return None


def _distancia_simple(a, b):
    """
    Distancia simple tipo levenshtein básica (rápida).
    """

    if a == b:
        return 0

    if abs(len(a) - len(b)) > 2:
        return 99

    errores = sum(1 for x, y in zip(a, b) if x != y)

    errores += abs(len(a) - len(b))

    return errores
