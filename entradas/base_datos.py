# entradas/base_datos.py

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
# VALIDADOR
# ==========================================================
def _es_hoja_estructura(df: pd.DataFrame) -> bool:

    cols = [_norm_col(c) for c in df.columns]

    return (
        "MATERIALES" in cols
        and "UNIDAD" in cols
        and any(c in cols for c in ["13.8", "34.5"])
    )


# ==========================================================
# NORMALIZADOR
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
# CARGA CENTRAL (ÚNICA)
# ==========================================================
def cargar_base_datos(ruta: Path | None = None) -> dict[str, pd.DataFrame]:

    ruta = ruta or obtener_ruta_base()

    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {ruta}")

    xls = pd.ExcelFile(ruta)

    hojas: dict[str, pd.DataFrame] = {}

    for hoja in xls.sheet_names:

        try:
            df = xls.parse(hoja)

            if df is None or df.empty:
                continue

            df = _normalizar_dataframe(df)
            nombre = _norm_col(hoja)

            # 🔥 CLAVE: incluir estructuras + catálogo
            if _es_hoja_estructura(df) or nombre == "MATERIALES":
                hojas[nombre] = df

        except Exception:
            continue

    if not hojas:
        raise ValueError("No se encontró ninguna hoja válida")

    return hojas


# ==========================================================
# ACCESO
# ==========================================================
def obtener_hoja(data: dict, nombre: str) -> pd.DataFrame | None:
    return data.get(_norm_col(nombre))


def obtener_catalogo_materiales(data: dict) -> pd.DataFrame:

    df = data.get("MATERIALES")

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(
            columns=["Materiales", "Unidad", "Codigo", "Referencia", "Costo Unitario"]
        )

    df = _normalizar_dataframe(df)

    out = pd.DataFrame()

    # ✔ SIEMPRE EXISTE
    out["Materiales"] = df["MATERIALES"].astype(str).str.strip()

    # 🔥 FIX: usar Series vacía en vez de ""
    def safe_col(nombre):
        if nombre in df.columns:
            return df[nombre]
        return pd.Series([""] * len(df))

    out["Unidad"] = safe_col("UNIDAD").astype(str).str.strip()
    out["Codigo"] = safe_col("CODIGO").astype(str).str.strip()
    out["Referencia"] = safe_col("REFERENCIA").astype(str).str.strip()

    # 🔥 FIX CRÍTICO
    costo_col = None
    for c in df.columns:
        if "COSTO" in c:
            costo_col = c
            break

    if costo_col:
        out["Costo Unitario"] = pd.to_numeric(df[costo_col], errors="coerce")
    else:
       out["Costo Unitario"] = pd.Series([None] * len(df))

    faltantes = out[out["Costo Unitario"].isna()]

    debug_guardar("CATALOGO_COSTOS", {
        "total": len(out),
        "con_costo": int(out["Costo Unitario"].notna().sum()),
        "sin_costo": int(len(faltantes)),
    })
    return out.reset_index(drop=True)
