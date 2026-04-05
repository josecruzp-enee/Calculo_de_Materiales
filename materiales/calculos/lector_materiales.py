# -*- coding: utf-8 -*-

import pandas as pd
import re


def leer_hoja_materiales(df: pd.DataFrame, tension: float) -> pd.DataFrame | None:
    """
    Procesa un DataFrame de materiales y devuelve:
    Materiales | Unidad | Cantidad
    """

    if df is None or df.empty:
        return None

    df = df.copy()
    df.columns = df.columns.map(str).str.strip()

    # =========================
    # Validar columnas base
    # =========================
    if "Materiales" not in df.columns:
        raise ValueError("Columna 'Materiales' no encontrada")

    if "Unidad" not in df.columns:
        df["Unidad"] = ""

    # =========================
    # Buscar columna de tensión (robusto)
    # =========================
    col_tension = None
    t_str = str(tension)

    for c in df.columns:
        if re.search(rf"\b{re.escape(t_str)}\b", str(c)):
            col_tension = c
            break

    if not col_tension:
        return None  # válido: no aplica esa tensión

    # =========================
    # Limpieza de datos
    # =========================
    df["Materiales"] = df["Materiales"].astype(str).str.strip()

    df[col_tension] = pd.to_numeric(df[col_tension], errors="coerce").fillna(0)

    # =========================
    # Filtrar
    # =========================
    df_out = df.loc[
        (df[col_tension] > 0) & (df["Materiales"] != ""),
        ["Materiales", "Unidad", col_tension]
    ].copy()

    df_out.rename(columns={col_tension: "Cantidad"}, inplace=True)

    # =========================
    # Validación final
    # =========================
    columnas_esperadas = {"Materiales", "Unidad", "Cantidad"}
    if not columnas_esperadas.issubset(df_out.columns):
        raise ValueError(f"Formato inválido: {df_out.columns}")

    return df_out if not df_out.empty else None
