# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd


def validar_estructuras(
    df: pd.DataFrame,
    df_indice: pd.DataFrame | None = None,
):

    errores = []

    # =====================================================
    # VALIDACIÓN BÁSICA (POST-NORMALIZACIÓN)
    # =====================================================
    if df is None or df.empty:
        return ["DataFrame de estructuras vacío"]

    columnas = set(c.lower().strip() for c in df.columns)

    requeridas = {
        "punto",
        "codigodeestructura",
        "cantidad"
    }

    faltantes = requeridas - columnas

    if faltantes:
        return [f"Faltan columnas requeridas: {list(faltantes)}"]

    # =====================================================
    # VALIDACIÓN CONTRA CATÁLOGO (OPCIONAL)
    # =====================================================
    if df_indice is None or df_indice.empty:
        return []

    df_indice.columns = df_indice.columns.str.strip().str.lower()

    if "codigodeestructura" in df_indice.columns:
        col_catalogo = "codigodeestructura"
    elif "estructura" in df_indice.columns:
        col_catalogo = "estructura"
    else:
        return ["Índice no tiene columna válida"]

    catalogo = set(
        df_indice[col_catalogo]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    codigos = (
        df["codigodeestructura"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    no_encontrados = sorted(set(c for c in codigos if c not in catalogo))

    if no_encontrados:
        errores.append(
            "Estructuras no encontradas en catálogo:\n"
            + "\n".join(no_encontrados)
        )

    return errores
