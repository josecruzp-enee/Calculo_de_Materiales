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
# LECTOR PRINCIPAL (ROBUSTO + DEBUG + CONTRATO)
# ==========================================================
def leer_hoja_materiales(df: pd.DataFrame, tension: float) -> pd.DataFrame | None:

    # =========================
    # DEBUG ENTRADA
    # =========================
    debug_guardar("lector_input_shape", getattr(df, "shape", None))
    debug_guardar("lector_input_columns_raw", list(df.columns) if df is not None else None)
    debug_guardar("lector_tension", tension)

    # =========================
    # VALIDACIONES
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

    # =========================
    # NORMALIZAR COLUMNAS (🔥 CLAVE)
    # =========================
    df.columns = [str(c).strip().upper() for c in df.columns]
    debug_guardar("lector_columns_normalized", list(df.columns))

    # =========================
    # DETECTAR COLUMNA MATERIALES
    # =========================
    posibles_material = [
        "MATERIALES",
        "MATERIAL",
        "DESCRIPCION",
        "DESCRIPCIÓN"
    ]

    col_material = None

    for c in df.columns:
        if c in posibles_material:
            col_material = c
            break

    if col_material is None:
        debug_guardar("lector_error", {
            "msg": "No se encontró columna de materiales",
            "columnas": list(df.columns)
        })
        raise ValueError(f"No se encontró columna de materiales: {df.columns}")

    df["Materiales"] = df[col_material]

    # =========================
    # UNIDAD
    # =========================
    if "UNIDAD" in df.columns:
        df["Unidad"] = df["UNIDAD"]
    else:
        df["Unidad"] = ""

    # =========================
    # DETECTAR COLUMNA TENSIÓN
    # =========================
    col_tension = None

    for c in df.columns:
        c_val = _parse_tension_col(c)

        if c_val is None:
            continue

        if abs(c_val - tension) < 0.1:
            col_tension = c
            break

    debug_guardar("lector_columna_tension", col_tension)

    if col_tension is None:
        debug_guardar("lector_warning", f"No se encontró columna de tensión {tension}")
        return None

    # =========================
    # LIMPIEZA
    # =========================
    df["Materiales"] = df["Materiales"].apply(_limpiar_str)
    df["Unidad"] = df["Unidad"].apply(_limpiar_str)

    df[col_tension] = pd.to_numeric(
        df[col_tension],
        errors="coerce"
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
    debug_guardar("lector_output_shape", df_out.shape)
    debug_guardar("lector_output_preview", df_out.head(10))

    # =========================
    # VALIDACIÓN FINAL (CONTRATO)
    # =========================
    if df_out.empty:
        debug_guardar("lector_resultado", "vacío")
        return None

    columnas_esperadas = {"Materiales", "Unidad", "Cantidad"}

    if not columnas_esperadas.issubset(df_out.columns):
        raise ValueError(f"Formato inválido: {df_out.columns}")

    debug_guardar("lector_resultado", "ok")

    return df_out
