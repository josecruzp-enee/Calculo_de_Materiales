# -*- coding: utf-8 -*-

from __future__ import annotations

import pandas as pd
from pathlib import Path

from entradas.leer_excel import leer_indice_materiales


# ==========================================================
# HELPERS
# ==========================================================
def _norm_codigo(x) -> str:
    if x is None:
        return ""
    return str(x).strip().upper()


# ==========================================================
# CARGA ÍNDICE NORMALIZADO
# ==========================================================
def cargar_indice_normalizado(ruta: str | Path) -> pd.DataFrame:
    """
    SALIDA:
    -------
    DataFrame con columnas:
        - CODIGO        → identificador único de la estructura
        - Descripcion   → descripción textual de la estructura
    """

    df = leer_indice_materiales(ruta)

    if df is None or df.empty:
        raise ValueError("El índice de estructuras está vacío")

    df = df.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]

    # ======================================================
    # VALIDACIÓN SIMPLE
    # ======================================================
    if "CODIGO" not in df.columns:
        raise ValueError("No existe columna CODIGO")

    if "DESCRIPCION" not in df.columns:
        df["DESCRIPCION"] = ""

    # ======================================================
    # CONSTRUIR DATAFRAME LIMPIO
    # ======================================================
    df_out = pd.DataFrame()

    df_out["CODIGO"] = df["CODIGO"].map(_norm_codigo)
    df_out = df_out[df_out["CODIGO"] != ""]

    df_out["Descripcion"] = df["DESCRIPCION"].fillna("").astype(str)

    return df_out.reset_index(drop=True)
