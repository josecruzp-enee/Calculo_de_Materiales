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
        df: DataFrame normalizado
        df_indice: catálogo (opcional)

    OUTPUT:
        lista de errores (list[str])

    NOTAS:
        - No modifica df
        - No hace parsing
        - No agrupa
    """

    errores = []

    # =====================================================
    # VALIDACIONES BÁSICAS
    # =====================================================
    if df is None or df.empty:
        return ["DataFrame de estructuras vacío"]

    if "codigodeestructura" not in df.columns:
        return ["Falta columna 'codigodeestructura'"]

    # =====================================================
    # NORMALIZACIÓN LOCAL (SEGURA)
    # =====================================================
    codigos = (
        df["codigodeestructura"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # =====================================================
    # SI NO HAY CATÁLOGO → SOLO VALIDACIÓN BÁSICA
    # =====================================================
    if df_indice is None or df_indice.empty:
        return []  # no validar contra catálogo

    if "codigodeestructura" not in df_indice.columns:
        return ["Índice no tiene 'codigodeestructura'"]

    catalogo = set(
        df_indice["codigodeestructura"]
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
