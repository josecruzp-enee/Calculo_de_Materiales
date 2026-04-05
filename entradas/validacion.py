# -*- coding: utf-8 -*-
"""
validacion.py (versión robusta producción)
"""

import pandas as pd


# =========================================================
# VALIDACIÓN PRINCIPAL
# =========================================================
def validar_estructuras(
    df: pd.DataFrame,
    df_indice: pd.DataFrame,
):
    """
    Valida estructuras contra catálogo.

    Retorna:
        df_validado (NO muta original)
        errores (list)
        warnings (list)
    """

    errores = []
    warnings = []

    if df is None or df.empty:
        raise ValueError("No hay estructuras para validar")

    col = "codigodeestructura"

    if col not in df.columns:
        raise ValueError(
            f"Columna requerida no encontrada: '{col}'. "
            f"Columnas disponibles: {list(df.columns)}"
        )

    if df_indice is None or df_indice.empty:
        warnings.append("⚠ Índice vacío → validación omitida")
        return df.copy(), errores, warnings

    # =====================================================
    # NORMALIZAR CATALOGO
    # =====================================================
    codigos_catalogo = set(
        df_indice[col]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df_out = df.copy()

    df_out[col] = (
        df_out[col]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    for i, codigo in enumerate(df_out[col]):

        if codigo in codigos_catalogo:
            continue

        sugerencia = _sugerir_codigo(codigo, codigos_catalogo)

        if sugerencia:
            warnings.append(
                f"Fila {i+1}: {codigo} no existe. Sugerido: {sugerencia}"
            )
        else:
            errores.append(
                f"Fila {i+1}: {codigo} no existe en catálogo"
            )

    return df_out, errores, warnings


# =========================================================
# SUGERENCIAS (MEJORADA)
# =========================================================
def _sugerir_codigo(codigo, catalogo):

    codigo = str(codigo).upper()

    mejor = None
    mejor_dist = 999

    for c in catalogo:
        d = _distancia_simple(codigo, c)

        if d < mejor_dist:
            mejor_dist = d
            mejor = c

    # más estricto
    if mejor_dist <= 1:
        return mejor

    return None


def _distancia_simple(a, b):
    """
    Distancia simple (segura, no agresiva)
    """

    if a == b:
        return 0

    if abs(len(a) - len(b)) > 1:
        return 999

    errores = sum(1 for x, y in zip(a, b) if x != y)
    errores += abs(len(a) - len(b))

    return errores
