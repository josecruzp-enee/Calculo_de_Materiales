# -*- coding: utf-8 -*-
"""
validacion.py

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
        df (posiblemente corregido)
        errores (list)
        warnings (list)
    """

    errores = []
    warnings = []

    if df is None or df.empty:
        raise ValueError("No hay estructuras para validar")

    # =====================================================
    # VALIDAR COLUMNAS
    # =====================================================
    col = "codigodeestructura"

    if col not in df.columns:
        raise ValueError(
            f"Columna requerida no encontrada: '{col}'. "
            f"Columnas disponibles: {list(df.columns)}"
        )

    if df_indice is None or df_indice.empty:
        warnings.append("⚠ Índice vacío → validación omitida")
        return df, errores, warnings

    # =====================================================
    # NORMALIZAR CATALOGO
    # =====================================================
    codigos_catalogo = set(
        df_indice[col]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # =====================================================
    # NORMALIZAR DF
    # =====================================================
    df[col] = (
        df[col]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # =====================================================
    # VALIDAR FILA A FILA (IMPORTANTE)
    # =====================================================
    codigos_corregidos = []

    for i, codigo in enumerate(df[col]):

        if codigo in codigos_catalogo:
            codigos_corregidos.append(codigo)
            continue

        sugerencia = _sugerir_codigo(codigo, codigos_catalogo)

        if sugerencia:
            warnings.append(
                f"⚠ Fila {i+1}: {codigo} → corregido a {sugerencia}"
            )
            codigos_corregidos.append(sugerencia)

        else:
            errores.append(
                f"❌ Fila {i+1}: {codigo} no existe en catálogo"
            )
            codigos_corregidos.append(codigo)

    # aplicar correcciones
    df[col] = codigos_corregidos

    # =====================================================
    # LOG
    # =====================================================
    if errores:
        log("❌ ERRORES:")
        for e in errores:
            log(e)

    if warnings:
        log("⚠ WARNINGS:")
        for w in warnings:
            log(w)

    return df, errores, warnings


# =========================================================
# SUGERENCIAS
# =========================================================

def _sugerir_codigo(codigo, catalogo):

    codigo = str(codigo).upper()

    mejor = None
    mejor_dist = 99

    for c in catalogo:
        d = _distancia_simple(codigo, c)

        if d < mejor_dist:
            mejor_dist = d
            mejor = c

    if mejor_dist <= 2:
        return mejor

    return None


def _distancia_simple(a, b):
    """
    Distancia simple tipo Levenshtein ligera.
    """

    if a == b:
        return 0

    if abs(len(a) - len(b)) > 2:
        return 99

    errores = sum(1 for x, y in zip(a, b) if x != y)
    errores += abs(len(a) - len(b))

    return errores
