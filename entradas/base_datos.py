# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from pathlib import Path


# ==========================================================
# CONFIG
# ==========================================================
def obtener_ruta_base() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "Estructura_datos.xlsx"


def _norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    return df


# ==========================================================
# CARGA BASE (SIN HEURÍSTICA)
# ==========================================================
def cargar_base_datos(ruta: Path | None = None) -> dict[str, pd.DataFrame]:
    ruta = ruta or obtener_ruta_base()

    if not ruta.exists():
        raise FileNotFoundError(f"No existe: {ruta}")

    xls = pd.ExcelFile(ruta)

    data: dict[str, pd.DataFrame] = {}

    for hoja in xls.sheet_names:
        df = xls.parse(hoja)
        if df is None or df.empty:
            continue

        nombre = str(hoja).strip().upper()
        data[nombre] = _norm_cols(df)

    return data


# ==========================================================
# ACCESO
# ==========================================================
def obtener_hoja(data: dict, nombre: str) -> pd.DataFrame | None:
    return data.get(str(nombre).strip().upper())


# ==========================================================
# CATÁLOGO DE ESTRUCTURAS (INDICE)
# ==========================================================
def cargar_catalogo_estructuras_desde_indice(data: dict) -> dict[str, str]:
    df = data.get("INDICE")

    if df is None:
        raise ValueError("Falta hoja INDICE")

    for col in ["CODIGO", "ESTRUCTURA"]:
        if col not in df.columns:
            raise ValueError(f"Falta columna en INDICE: {col}")

    mapa = dict(zip(
        df["CODIGO"].astype(str).str.strip().str.upper(),
        df["ESTRUCTURA"].astype(str).str.strip()
    ))

    return mapa


# ==========================================================
# CATÁLOGO DE MATERIALES
# ==========================================================
# ==========================================================
# CATÁLOGO DE MATERIALES
# ==========================================================
def obtener_catalogo_materiales(data: dict) -> pd.DataFrame:

    df = data.get("MATERIALES")

    if df is None:
        raise ValueError("Falta hoja MATERIALES")

    columnas_requeridas = [
        "CODIGO",
        "MATERIALES",
        "UNIDAD",
        "REFERENCIA",
        "COSTO UNITARIO",
    ]

    for col in columnas_requeridas:
        if col not in df.columns:
            raise ValueError(
                f"Falta columna '{col}' en hoja MATERIALES. "
                f"Columnas disponibles: {list(df.columns)}"
            )

    out = pd.DataFrame()

    out["Codigo"] = (
        df["CODIGO"]
        .astype(str)
        .str.strip()
    )

    out["Materiales"] = (
        df["MATERIALES"]
        .astype(str)
        .str.strip()
    )

    out["Unidad"] = (
        df["UNIDAD"]
        .astype(str)
        .str.strip()
    )

    out["Referencia"] = (
        df["REFERENCIA"]
        .astype(str)
        .str.strip()
    )

    out["Costo"] = pd.to_numeric(
        df["COSTO UNITARIO"],
        errors="coerce"
    )

    return out.reset_index(drop=True)
