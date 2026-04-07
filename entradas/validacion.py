# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd


def validar_estructuras(
    df: pd.DataFrame,
    df_indice: pd.DataFrame | None = None,
):
    """
    Valida estructuras contra catálogo.

    INPUT:
        df: DataFrame normalizado (Punto, Estructura, Cantidad)
        df_indice: catálogo (opcional)

    OUTPUT:
        lista de errores (list[str])
    """

    errores = []

    # =====================================================
    # VALIDACIONES BÁSICAS
    # =====================================================
    if df is None or df.empty:
        return ["DataFrame de estructuras vacío"]

    if "Estructura" not in df.columns:
        return ["Falta columna 'Estructura'"]

    # =====================================================
    # NORMALIZACIÓN LOCAL
    # =====================================================
    codigos = (
        df["Estructura"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # =====================================================
    # VALIDACIÓN BÁSICA (sin catálogo)
    # =====================================================
    if df_indice is None or df_indice.empty:
        return []

    # =====================================================
    # NORMALIZAR CATÁLOGO
    # =====================================================
    df_indice.columns = df_indice.columns.str.strip().str.lower()

    if "codigodeestructura" in df_indice.columns:
        col_catalogo = "codigodeestructura"
    elif "estructura" in df_indice.columns:
        col_catalogo = "estructura"
    else:
        return ["Índice no tiene columna de estructuras válida"]

    catalogo = set(
        df_indice[col_catalogo]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    no_encontrados = sorted(set(c for c in codigos if c not in catalogo))

    if no_encontrados:
        errores.append(
            "Estructuras no encontradas en catálogo:\n"
            + "\n".join(no_encontrados)
        )

    return errores
