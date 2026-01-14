# -*- coding: utf-8 -*-
"""
indice_estructuras.py
Carga y normalización del índice de estructuras + construcción de DFs de resumen.
"""

import pandas as pd

from modulo.entradas import cargar_indice
from servicios.normalizacion_estructuras import _normalizar_codigo_basico


def cargar_indice_normalizado(archivo_materiales, log) -> pd.DataFrame:
    df_indice = cargar_indice(archivo_materiales)

    log("Columnas originales índice: " + str(df_indice.columns.tolist()))
    df_indice = df_indice.copy()
    df_indice.columns = df_indice.columns.str.strip().str.lower()

    if "código de estructura" in df_indice.columns:
        df_indice.rename(columns={"código de estructura": "codigodeestructura"}, inplace=True)
    if "codigo de estructura" in df_indice.columns:
        df_indice.rename(columns={"codigo de estructura": "codigodeestructura"}, inplace=True)

    if "descripcion" in df_indice.columns:
        df_indice.rename(columns={"descripcion": "Descripcion"}, inplace=True)

    if "codigodeestructura" not in df_indice.columns:
        df_indice["codigodeestructura"] = ""
    df_indice["codigodeestructura"] = df_indice["codigodeestructura"].astype(str).map(_normalizar_codigo_basico)

    if "Descripcion" not in df_indice.columns:
        df_indice["Descripcion"] = ""
    else:
        df_indice["Descripcion"] = df_indice["Descripcion"].fillna("").astype(str)

    log("Columnas normalizadas índice: " + str(df_indice.columns.tolist()))
    log("Primeras filas índice:\n" + str(df_indice.head(10)))

    return df_indice


def construir_df_estructuras_resumen(df_indice: pd.DataFrame, conteo: dict, log) -> pd.DataFrame:
    conteo_norm = {str(k).strip().upper(): int(v) for k, v in conteo.items()}
    df = df_indice.copy()
    df["Cantidad"] = df["codigodeestructura"].map(conteo_norm).fillna(0).astype(int)
    df_res = df[df["Cantidad"] > 0].copy()
    log("df_estructuras_resumen:\n" + str(df_res.head(50)))
    return df_res


def construir_df_estructuras_por_punto(tmp_explotado: pd.DataFrame, df_indice: pd.DataFrame, log) -> pd.DataFrame:
    df_pp = tmp_explotado.merge(
        df_indice[["codigodeestructura", "Descripcion"]],
        on="codigodeestructura",
        how="left"
    )
    df_pp["Descripcion"] = df_pp["Descripcion"].fillna("NO ENCONTRADA")
    df_pp.rename(columns={"cantidad": "Cantidad"}, inplace=True)
    df_pp = df_pp[["Punto", "codigodeestructura", "Descripcion", "Cantidad"]].copy()
    log("df_estructuras_por_punto:\n" + str(df_pp.head(50)))
    return df_pp
