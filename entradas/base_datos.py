# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from pathlib import Path


# ==========================================================
# CONFIG
# ==========================================================
def obtener_ruta_base() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "Estructura_datos.xlsx"


def _norm_col(s: str) -> str:
    return str(s).strip().upper()


# ==========================================================
# CARGA BASE
# ==========================================================
def cargar_base_datos(ruta: Path | None = None) -> dict[str, pd.DataFrame]:

    ruta = ruta or obtener_ruta_base()

    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {ruta}")

    try:
        xls = pd.ExcelFile(ruta)
    except Exception as e:
        raise RuntimeError(f"Error al abrir el archivo Excel: {e}")

    hojas: dict[str, pd.DataFrame] = {}

    for hoja in xls.sheet_names:
        try:
            df = xls.parse(hoja)

            if df is None or df.empty:
                continue

            df.columns = df.columns.map(_norm_col)

            nombre = _norm_col(hoja)

            hojas[nombre] = df

        except Exception:
            continue

    if not hojas:
        raise ValueError("No se pudo cargar ninguna hoja válida")

    return hojas


# ==========================================================
# ACCESO
# ==========================================================
def obtener_hoja(data: dict, nombre: str) -> pd.DataFrame | None:
    if not data:
        return None
    return data.get(_norm_col(nombre))


# ==========================================================
# CATÁLOGO
# ==========================================================
def obtener_catalogo_materiales(data: dict) -> pd.DataFrame:

    df = obtener_hoja(data, "MATERIALES")

    if df is None or df.empty:
        return pd.DataFrame(
            columns=["Materiales", "Unidad", "Codigo", "Referencia", "Costo"]
        )

    df = df.copy()

    cols = {_norm_col(c): c for c in df.columns}

    col_mat = cols.get("DESCRIPCION DE MATERIALES")

    if not col_mat:
        raise ValueError("No existe columna de materiales")

    df_out = pd.DataFrame()

    df_out["Materiales"] = df[col_mat].astype(str).str.strip()

    df_out["Unidad"] = df.get(cols.get("UNIDAD", ""), "").astype(str).str.strip()

    df_out["Codigo"] = df.get(cols.get("CODIGO", ""), "").astype(str).str.strip()

    df_out["Referencia"] = df.get(cols.get("REFERENCIA", ""), "").astype(str).str.strip()

    df_out["Costo"] = pd.to_numeric(
        df.get(cols.get("COSTO UNITARIO", ""), 0),
        errors="coerce"
    ).fillna(0)

    return df_out.reset_index(drop=True)
