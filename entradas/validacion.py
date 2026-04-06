# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd


def validar_estructuras(
    df: pd.DataFrame,
    df_indice: pd.DataFrame,
):
    """
    Valida estructuras contra catálogo.

    REQUIERE:
        df ya normalizado (una estructura por fila)

    NO hace parsing.
    """

    errores = []
    warnings = []

    # =========================
    # VALIDACIONES BÁSICAS
    # =========================
    if df is None or df.empty:
        return df, ["DataFrame de estructuras vacío"], []

    if df_indice is None or df_indice.empty:
        return df, ["Índice de estructuras vacío"], []

    if "codigodeestructura" not in df.columns:
        return df, ["Falta columna 'codigodeestructura'"], []

    if "codigodeestructura" not in df_indice.columns:
        return df, ["Índice no tiene 'codigodeestructura'"], []

    # =========================
    # NORMALIZACIÓN SEGURA
    # =========================
    df = df.copy()
    df_indice = df_indice.copy()

    df["codigodeestructura"] = (
        df["codigodeestructura"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df_indice["codigodeestructura"] = (
        df_indice["codigodeestructura"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # =========================
    # CATÁLOGO
    # =========================
    catalogo = set(df_indice["codigodeestructura"])

    # =========================
    # VALIDACIÓN EFICIENTE
    # =========================
    codigos = set(df["codigodeestructura"])

    no_encontrados = sorted(c for c in codigos if c not in catalogo)

    # =========================
    # ERRORES
    # =========================
    if no_encontrados:
        errores.append(
            "Estructuras no encontradas en catálogo:\n"
            + "\n".join(no_encontrados)
        )

    return df, errores, warnings
