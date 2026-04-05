# -*- coding: utf-8 -*-

import pandas as pd
import re


def leer_hoja_materiales(df: pd.DataFrame, tension: float) -> pd.DataFrame | None:
    """
    Procesa un DataFrame de materiales y devuelve:
    Materiales | Unidad | Cantidad
    """

    # =========================
    # VALIDACIÓN FUERTE
    # =========================
    if df is None or df.empty:
        return None

    if tension is None:
        raise ValueError("tension es None")

    try:
        tension = float(tension)
    except Exception:
        raise ValueError(f"tension inválida: {tension}")

    df = df.copy()
    df.columns = df.columns.map(str).str.strip()

    # =========================
    # VALIDAR COLUMNAS BASE
    # =========================
    if "Materiales" not in df.columns:
        raise ValueError("Columna 'Materiales' no encontrada")

    if "Unidad" not in df.columns:
        df["Unidad"] = ""

    # =========================
    # BUSCAR COLUMNA DE TENSIÓN (MEJORADO)
    # =========================
    col_tension = None

    for c in df.columns:
        try:
            c_num = float(str(c).replace("KV", "").replace("kV", "").strip())
            if abs(c_num - tension) < 0.01:
                col_tension = c
                break
        except:
            continue

    if col_tension is None:
        return None  # válido

    # =========================
    # LIMPIEZA
    # =========================
    df["Materiales"] = df["Materiales"].astype(str).str.strip()

    df[col_tension] = pd.to_numeric(
        df[col_tension], errors="coerce"
    ).fillna(0)

    # =========================
    # FILTRO SEGURO
    # =========================
    mask = (df[col_tension] > 0) & (df["Materiales"] != "")

    df_out = df.loc[
        mask,
        ["Materiales", "Unidad", col_tension]
    ].copy()

    df_out.rename(columns={col_tension: "Cantidad"}, inplace=True)

    # =========================
    # VALIDACIÓN FINAL
    # =========================
    if df_out.empty:
        return None

    columnas_esperadas = {"Materiales", "Unidad", "Cantidad"}

    if not columnas_esperadas.issubset(df_out.columns):
        raise ValueError(f"Formato inválido: {df_out.columns}")

    return df_out
