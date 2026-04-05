# -*- coding: utf-8 -*-

from __future__ import annotations

import pandas as pd
from pathlib import Path

from entradas.leer_excel import leer_indice_materiales


# ==========================================================
# HELPERS
# ==========================================================
def _norm_col(s: str) -> str:
    return str(s).strip().upper().replace("Á", "A")


def _norm_codigo(x) -> str:
    if x is None:
        return ""
    return str(x).strip().upper()


# ==========================================================
# CARGA ÍNDICE NORMALIZADO
# ==========================================================
def cargar_indice_normalizado(ruta: str | Path) -> pd.DataFrame:

    df = leer_indice_materiales(ruta)

    if df is None or df.empty:
        raise ValueError("El índice de estructuras está vacío")

    df = df.copy()

    # =========================
    # NORMALIZAR COLUMNAS
    # =========================
    cols = {_norm_col(c): c for c in df.columns}

    col_codigo = None

    for key in cols:
        if "CODIGO" in key and "ESTRUCTURA" in key:
            col_codigo = cols[key]
            break

    if not col_codigo:
        raise ValueError("No se encontró columna de código de estructura")

    col_desc = None
    for key in cols:
        if "DESCRIP" in key:
            col_desc = cols[key]
            break

    # =========================
    # CONSTRUIR DATAFRAME
    # =========================
    df_out = pd.DataFrame()

    df_out["codigodeestructura"] = (
        df[col_codigo]
        .astype(str)
        .map(_norm_codigo)
    )

    df_out = df_out[df_out["codigodeestructura"] != ""]

    if col_desc:
        df_out["Descripcion"] = (
            df[col_desc]
            .fillna("")
            .astype(str)
        )
    else:
        df_out["Descripcion"] = ""

    return df_out.reset_index(drop=True)
