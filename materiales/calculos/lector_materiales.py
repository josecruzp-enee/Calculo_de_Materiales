# -*- coding: utf-8 -*-

import pandas as pd
import re
from ayuda.debug import debug_guardar


# ==========================================================
# HELPERS
# ==========================================================
def _limpiar_str(v) -> str:
    if pd.isna(v):
        return ""
    return str(v).strip()


def _parse_tension_col(col) -> float | None:
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

    # =========================
    # DEBUG ENTRADA
    # =========================
    debug_guardar("lector_input_shape", getattr(df, "shape", None))
    debug_guardar("lector_input_columns", list(df.columns) if df is not None else None)
    debug_guardar("lector_tension", tension)

    # =========================
    # VALIDACIÓN FUERTE
    # =========================
    if df is None or df.empty:
        debug_guardar("lector_error", "df vacío o None")
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
    # DEBUG COLUMNAS LIMPIAS
    # =========================
    debug_guardar("lector_columns_clean", list(df.columns))

    # =========================
    # VALIDAR COLUMNAS BASE
    # =========================
    if "Materiales" not in df.columns:
        debug_guardar("lector_error", {
            "msg": "Columna 'Materiales' no encontrada",
            "columnas": list(df.columns)
        })
        raise ValueError("Columna 'Materiales' no encontrada")

    if "Unidad" not in df.columns:
        df["Unidad"] = ""

    # =========================
    # BUSCAR COLUMNA DE TENSIÓN
    # =========================
    col_tension = None

    for c in df.columns:
        c_val = _parse_tension_col(c)

        if c_val is None:
            continue

        if abs(c_val - tension) < 0.05:
            col_tension = c
            break

    debug_guardar("lector_columna_tension", col_tension)

    if col_tension is None:
        debug_guardar("lector_warning", "No se encontró columna de tensión")
        return None

    # =========================
    # LIMPIEZA
    # =========================
    df["Materiales"] = df["Materiales"].apply(_limpiar_str)
    df["Unidad"] = df["Unidad"].apply(_limpiar_str)

    df[col_tension] = pd.to_numeric(
        df[col_tension], errors="coerce"
    ).fillna(0)

    # =========================
    # FILTRO
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
    # DEBUG SALIDA
    # =========================
    debug_guardar("lector_output_preview", df_out.head(10))
    debug_guardar("lector_output_shape", df_out.shape)

    # =========================
    # VALIDACIÓN FINAL
    # =========================
    if df_out.empty:
        debug_guardar("lector_resultado", "vacío")
        return None

    columnas_esperadas = {"Materiales", "Unidad", "Cantidad"}

    if not columnas_esperadas.issubset(df_out.columns):
        raise ValueError(f"Formato inválido: {df_out.columns}")

    debug_guardar("lector_resultado", "ok")

    return df_out
