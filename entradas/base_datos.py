# -*- coding: utf-8 -*-

from __future__ import annotations

import pandas as pd
from pathlib import Path


# ==========================================================
# CONFIG
# ==========================================================
def obtener_ruta_base() -> Path:
    """
    Permite cambiar fácilmente la ubicación del archivo en el futuro.
    """
    return Path(__file__).resolve().parent.parent / "data" / "Estructura_datos.xlsx"


# ==========================================================
# CARGA BASE DE DATOS
# ==========================================================
def cargar_base_datos() -> dict[str, pd.DataFrame]:
    """
    Carga todas las hojas del Excel en memoria.

    Retorna:
        dict[str, DataFrame]
    """

    ruta = obtener_ruta_base()

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

            nombre = str(hoja).strip().upper()

            df.columns = df.columns.map(str).str.strip()

            hojas[nombre] = df

        except Exception as e:
            print(f"[WARN] Error leyendo hoja '{hoja}': {e}")
            continue

    if not hojas:
        raise ValueError("No se pudo cargar ninguna hoja válida del archivo.")

    return hojas


# ==========================================================
# ACCESO SEGURO A HOJAS
# ==========================================================
def obtener_hoja(data: dict, nombre: str) -> pd.DataFrame | None:
    """
    Devuelve una hoja de forma segura (case insensitive).
    """
    if not data:
        return None

    return data.get(nombre.strip().upper())


# ==========================================================
# CATÁLOGO GLOBAL DE MATERIALES
# ==========================================================
def obtener_catalogo_materiales(data: dict) -> pd.DataFrame:
    """
    Extrae y normaliza el catálogo desde la hoja 'MATERIALES'.

    Salida estándar:
        ["Materiales", "Unidad", "Codigo", "Referencia", "Costo"]
    """

    df = obtener_hoja(data, "MATERIALES")

    if df is None or df.empty:
        return pd.DataFrame(
            columns=["Materiales", "Unidad", "Codigo", "Referencia", "Costo"]
        )

    df = df.copy()
    df.columns = df.columns.map(str).str.strip()

    # =========================
    # Validación mínima
    # =========================
    if "DESCRIPCIÓN DE MATERIALES" not in df.columns:
        raise ValueError("No existe columna 'DESCRIPCIÓN DE MATERIALES'")

    # =========================
    # Construcción estándar
    # =========================
    df_out = pd.DataFrame()

    df_out["Materiales"] = (
        df["DESCRIPCIÓN DE MATERIALES"]
        .astype(str)
        .str.strip()
    )

    df_out["Unidad"] = (
        df.get("Unidad", "")
        .astype(str)
        .str.strip()
    )

    df_out["Codigo"] = (
        df.get("CÓDIGO", "")
        .astype(str)
        .str.strip()
    )

    df_out["Referencia"] = (
        df.get("REFERENCIA", "")
        .astype(str)
        .str.strip()
    )

    df_out["Costo"] = pd.to_numeric(
        df.get("Costo Unitario", 0),
        errors="coerce"
    ).fillna(0)

    # =========================
    # Limpieza final
    # =========================
    df_out = (
        df_out[df_out["Materiales"] != ""]
        .drop_duplicates(subset=["Materiales"])
        .reset_index(drop=True)
    )

    return df_out


# ==========================================================
# UTILIDADES
# ==========================================================
def obtener_lista_materiales(data: dict) -> list[str]:
    """
    Devuelve lista simple de materiales (para UI).
    """
    df = obtener_catalogo_materiales(data)

    if df.empty:
        return []

    return df["Materiales"].tolist()


def obtener_material_por_codigo(data: dict, codigo: str) -> dict | None:
    """
    Busca material por código.
    """

    df = obtener_catalogo_materiales(data)

    if df.empty:
        return None

    df_filtrado = df[df["Codigo"].str.upper() == codigo.strip().upper()]

    if df_filtrado.empty:
        return None

    return df_filtrado.iloc[0].to_dict()
