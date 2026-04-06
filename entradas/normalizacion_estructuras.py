# -*- coding: utf-8 -*-
"""
normalizacion_estructuras.py

Normalización ROBUSTA de estructuras.

Entrada:
    DataFrame en cualquier formato

Salida:
    - estructuras_por_punto
    - conteo_global
    - df_normalizado
    - errores
    - warnings
"""

from __future__ import annotations
import pandas as pd
from collections import Counter

# 🔥 IMPORTANTE (usa tu módulo bueno)
from materiales.auxiliares.materiales_aux import (
    expandir_lista_codigos,
    limpiar_codigo,
)


# ==========================================================
# DETECCIÓN DE FORMATO
# ==========================================================
def _es_formato_largo(df: pd.DataFrame) -> bool:
    cols = [c.lower().strip() for c in df.columns]

    return (
        "punto" in cols
        and ("codigodeestructura" in cols or "estructura" in cols)
    )


# ==========================================================
# CONVERSIÓN A FORMATO LARGO
# ==========================================================
def _convertir_a_largo(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()
    df.columns = df.columns.str.strip()

    registros = []

    for _, row in df.iterrows():

        punto = row.get("Punto") or row.get("punto")

        # buscar columna de estructuras
        estructura_raw = None

        for col in df.columns:
            if col.lower() in ["estructura", "estructuras", "codigodeestructura"]:
                estructura_raw = row.get(col)
                break

        if estructura_raw is None:
            continue

        # 🔥 AQUÍ ESTÁ LA CLAVE
        lista_codigos = expandir_lista_codigos(estructura_raw)

        for cod in lista_codigos:
            cod = limpiar_codigo(cod)

            if not cod:
                continue

            registros.append({
                "Punto": punto,
                "codigodeestructura": cod,
                "cantidad": 1
            })

    return pd.DataFrame(registros)


# ==========================================================
# NORMALIZACIÓN PRINCIPAL
# ==========================================================
def construir_estructuras_por_punto_y_conteo(df: pd.DataFrame):

    errores = []
    warnings = []

    if df is None or df.empty:
        return {}, Counter(), pd.DataFrame(), ["DataFrame vacío"], []

    df = df.copy()

    # ======================================================
    # FORMATO
    # ======================================================
    if _es_formato_largo(df):
        df_base = df.copy()
    else:
        df_base = _convertir_a_largo(df)

    if df_base.empty:
        return {}, Counter(), df_base, ["No se pudo normalizar"], []

    # ======================================================
    # LIMPIEZA FINAL
    # ======================================================
    df_base.columns = df_base.columns.str.strip().str.lower()

    if "punto" not in df_base.columns:
        errores.append("Falta columna Punto")
        return {}, Counter(), df_base, errores, warnings

    if "codigodeestructura" not in df_base.columns:
        errores.append("Falta columna codigodeestructura")
        return {}, Counter(), df_base, errores, warnings

    df_base["punto"] = df_base["punto"].astype(str).str.strip()
    df_base["codigodeestructura"] = df_base["codigodeestructura"].astype(str).str.strip()

    # ======================================================
    # AGRUPACIÓN
    # ======================================================
    df_final = (
        df_base
        .groupby(["punto", "codigodeestructura"], as_index=False)
        .size()
        .rename(columns={"size": "cantidad"})
    )

    # ======================================================
    # ESTRUCTURAS POR PUNTO
    # ======================================================
    estructuras_por_punto = {}

    for _, row in df_final.iterrows():
        p = row["punto"]
        c = row["codigodeestructura"]
        n = row["cantidad"]

        if p not in estructuras_por_punto:
            estructuras_por_punto[p] = {}

        estructuras_por_punto[p][c] = n

    # ======================================================
    # CONTEO GLOBAL
    # ======================================================
    conteo_global = Counter()

    for _, row in df_final.iterrows():
        conteo_global[row["codigodeestructura"]] += row["cantidad"]

    return estructuras_por_punto, conteo_global, df_final, errores, warnings
