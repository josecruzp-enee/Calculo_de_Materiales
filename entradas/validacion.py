# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd


# =========================================================
# VALIDACIÓN DE ESTRUCTURAS (SIN DEPENDENCIAS OCULTAS)
# =========================================================
def validar_estructuras(
    df: pd.DataFrame,
    df_indice: pd.DataFrame,
):
    """
    Valida que las estructuras existan en el catálogo.

    ENTRADA:
        df → DataFrame normalizado
        df_indice → índice ya cargado (NO se carga aquí)

    SALIDA:
        df_validado, errores, warnings
    """

    errores = []
    warnings = []

    # =========================
    # VALIDACIONES BÁSICAS
    # =========================
    if df is None or df.empty:
        errores.append("DataFrame de estructuras vacío")
        return df, errores, warnings

    if df_indice is None or df_indice.empty:
        errores.append("Índice de estructuras vacío")
        return df, errores, warnings

    if "codigodeestructura" not in df.columns:
        errores.append("Falta columna 'codigodeestructura'")
        return df, errores, warnings

    if "codigodeestructura" not in df_indice.columns:
        errores.append("Índice no tiene 'codigodeestructura'")
        return df, errores, warnings

    # =========================
    # NORMALIZAR TEXTO
    # =========================
    df = df.copy()
    df_indice = df_indice.copy()

    df["codigodeestructura"] = (
        df["codigodeestructura"].astype(str).str.strip().str.upper()
    )

    df_indice["codigodeestructura"] = (
        df_indice["codigodeestructura"].astype(str).str.strip().str.upper()
    )

    # =========================
    # SET DE VALIDACIÓN
    # =========================
    catalogo = set(df_indice["codigodeestructura"])

    # =========================
    # VALIDAR UNO A UNO
    # =========================
    no_encontrados = []

    for cod in df["codigodeestructura"].unique():
        if cod not in catalogo:
            no_encontrados.append(cod)

    if no_encontrados:
        errores.append(
            "Estructuras no encontradas en catálogo:\n"
            + "\n".join(sorted(no_encontrados))
        )

    # =========================
    # OUTPUT
    # =========================
    return df, errores, warnings
