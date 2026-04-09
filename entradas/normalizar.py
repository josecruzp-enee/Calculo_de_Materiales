# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import re


# =========================================================
# NORMALIZACIÓN SIMPLE Y ESTABLE
# =========================================================
def normalizar_estructuras(df: pd.DataFrame):

    errores = []
    warnings = []

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        errores.append("df_estructuras vacío o inválido")
        return pd.DataFrame(), errores, warnings

    df = df.copy()

    if "Estructura" not in df.columns:
        errores.append("Falta columna 'Estructura'")
        return pd.DataFrame(), errores, warnings

    df["Estructura"] = (
        df["Estructura"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df = df[df["Estructura"] != ""]

    if df.empty:
        errores.append("No quedaron estructuras válidas")

    return df, errores, warnings
