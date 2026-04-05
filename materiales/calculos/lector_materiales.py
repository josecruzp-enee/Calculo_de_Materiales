# -*- coding: utf-8 -*-

import pandas as pd
import re


# ==========================================================
# HELPERS
# ==========================================================
def _limpiar_str(v) -> str:
    if pd.isna(v):
        return ""
    return str(v).strip()


def _parse_tension_col(col) -> float | None:
    """
    Extrae valor numérico de columnas tipo:
    13.8, 13.8 kV, 13,8KV, etc.
    """
    if col is None:
        return None

    txt = str(col).upper().replace(",", ".")
    txt = re.sub(r"[^\d\.]", "", txt)

    try:
        return float(txt)
    except Exception:
        return None


# ==========================================================
# LECTOR PRINCIPAL
# ==========================================================
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
    # BUSCAR COLUMNA DE TENSIÓN (ROBUSTO)
    # =========================
    col_tension = None

    for c in df.columns:
        c_val = _parse_tension_col(c)

        if c_val is None:
            continue

        if abs(c_val - tension) < 0.05:
            col_tension = c
            break

    if col_tension is None:
        return None  # válido pero sin datos

    # =========================
    # LIMPIEZA
    # =========================
    df["Materiales"] = df["Materiales"].apply(_limpiar_str)
    df["Unidad"] = df["Unidad"].apply(_limpiar_str)

    df[col_tension] = pd.to_numeric(
        df[col_tension], errors="coerce"
    ).fillna(0)

    # =========================
    # FILTRO SEGURO (🔥 CLAVE)
    # =========================
    mask = (
        (df[col_tension] > 0)
        & (df["Materiales"] != "")
        & (~df["Materiales"].str.lower().isin(["nan", "none"]))
    )

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
