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
    return (
        str(s)
        .strip()
        .upper()
        .replace("Á", "A")
        .replace("É", "E")
        .replace("Í", "I")
        .replace("Ó", "O")
        .replace("Ú", "U")
    )


# ==========================================================
# VALIDADOR DE HOJAS DE ESTRUCTURA
# ==========================================================
def _es_hoja_estructura(df: pd.DataFrame) -> bool:

    cols = [_norm_col(c) for c in df.columns]

    return (
        "MATERIALES" in cols
        and "UNIDAD" in cols
        and any(c in cols for c in ["13.8", "34.5"])
    )


# ==========================================================
# NORMALIZAR COLUMNAS DE HOJA
# ==========================================================
def _normalizar_dataframe(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()

    df.columns = [_norm_col(c) for c in df.columns]

    mapa = {
        "MATERIAL": "MATERIALES",
        "DESCRIPCION": "MATERIALES",
        "DESCRIPCION DE MATERIALES": "MATERIALES",

        "UNIDAD": "UNIDAD",

        "CANTIDAD": "CANTIDAD",
    }

    df = df.rename(columns=lambda c: mapa.get(c, c))

    return df


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

            df = _normalizar_dataframe(df)

            nombre = _norm_col(hoja)

            # 🔥 SOLO GUARDAR HOJAS DE ESTRUCTURA
            if _es_hoja_estructura(df):
                hojas[nombre] = df

        except Exception:
            continue

    if not hojas:
        raise ValueError("No se encontró ninguna hoja de estructura válida")

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

    # ⚠️ Aquí buscamos directamente la hoja original
    ruta = obtener_ruta_base()
    xls = pd.ExcelFile(ruta)

    if "Materiales" not in xls.sheet_names:
        return pd.DataFrame(
            columns=["Materiales", "Unidad", "Codigo", "Referencia", "Costo"]
        )

    df = xls.parse("Materiales")

    df = _normalizar_dataframe(df)

    if "MATERIALES" not in df.columns:
        raise ValueError(f"Columnas disponibles: {list(df.columns)}")

    df_out = pd.DataFrame()

    df_out["Materiales"] = df["MATERIALES"].astype(str).str.strip()

    df_out["Unidad"] = df.get("UNIDAD", "").astype(str).str.strip()

    df_out["Codigo"] = df.get("CODIGO", "").astype(str).str.strip()

    df_out["Referencia"] = df.get("REFERENCIA", "").astype(str).str.strip()

    df_out["Costo"] = pd.to_numeric(
        df.get("COSTO UNITARIO", 0),
        errors="coerce"
    ).fillna(0)

    return df_out.reset_index(drop=True)
