# -*- coding: utf-8 -*-
"""
core/costos_materiales.py

Contrato oficial para costos de materiales.

Responsabilidad:
- Leer precios (Excel o DataFrame)
- Enriquecer df_resumen con precios
- Calcular costos (interno)
- Generar precios de venta (cliente)

NO hace:
- Correcciones silenciosas
- Suposiciones ocultas
"""

from __future__ import annotations

import pandas as pd
import unicodedata


# =========================================================
# NORMALIZACIÓN TEXTO
# =========================================================
def _norm_txt(s: object) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""

    t = str(s).strip()

    t = "".join(
        c for c in unicodedata.normalize("NFD", t)
        if unicodedata.category(c) != "Mn"
    )

    t = " ".join(t.split())

    return t.upper()


# =========================================================
# CARGAR PRECIOS
# =========================================================
def cargar_precios(archivo_materiales: str) -> pd.DataFrame:

    try:
        xls = pd.ExcelFile(archivo_materiales)

        if "precios" in xls.sheet_names:
            hoja = "precios"
        elif "Materiales" in xls.sheet_names:
            hoja = "Materiales"
        elif "materiales" in xls.sheet_names:
            hoja = "materiales"
        else:
            hoja = xls.sheet_names[0]

        df = pd.read_excel(archivo_materiales, sheet_name=hoja)

    except Exception as e:
        raise RuntimeError(f"Error cargando archivo de precios: {e}")

    # -------------------------------
    # LIMPIEZA COLUMNAS
    # -------------------------------
    df.columns = [str(c).replace("\u00A0", " ").strip() for c in df.columns]

    # -------------------------------
    # RENOMBRE FLEXIBLE
    # -------------------------------
    ren = {}

    for c in df.columns:
        cc = c.lower().strip()

        if cc.startswith("material") or "descrip" in cc:
            ren[c] = "Materiales"

        elif cc.startswith("unidad"):
            ren[c] = "Unidad"

        elif "precio" in cc or "costo unitario" in cc or cc.startswith("costo"):
            ren[c] = "Precio Unitario"

        elif "moneda" in cc:
            ren[c] = "Moneda"

    df = df.rename(columns=ren)

    # -------------------------------
    # VALIDACIÓN
    # -------------------------------
    if "Materiales" not in df.columns:
        raise ValueError("No se encontró columna de materiales")

    if "Precio Unitario" not in df.columns:
        raise ValueError("No se encontró columna de precio")

    if "Unidad" not in df.columns:
        df["Unidad"] = ""

    if "Moneda" not in df.columns:
        df["Moneda"] = "L"

    # -------------------------------
    # LIMPIEZA DATOS
    # -------------------------------
    df["Materiales"] = df["Materiales"].astype(str).str.strip()
    df["Unidad"] = df["Unidad"].astype(str).str.strip()
    df["Moneda"] = df["Moneda"].astype(str).str.strip()

    df.loc[df["Moneda"].eq(""), "Moneda"] = "L"

    df["Precio Unitario"] = pd.to_numeric(
        df["Precio Unitario"], errors="coerce"
    )

    # -------------------------------
    # NORMALIZACIÓN
    # -------------------------------
    df["Materiales_norm"] = df["Materiales"].map(_norm_txt)
    df["Unidad_norm"] = df["Unidad"].map(_norm_txt)

    out = df[
        ["Materiales_norm", "Unidad_norm", "Precio Unitario", "Moneda"]
    ].copy()

    out = out.drop_duplicates(
        subset=["Materiales_norm", "Unidad_norm"],
        keep="first"
    )

    return out


# =========================================================
# COSTO INTERNO
# =========================================================
def calcular_costos_desde_resumen(
    df_resumen: pd.DataFrame,
    precios_o_archivo
) -> pd.DataFrame:

    if df_resumen is None or df_resumen.empty:
        raise ValueError("df_resumen vacío")

    required = {"Materiales", "Cantidad"}
    if not required.issubset(df_resumen.columns):
        raise ValueError(f"df_resumen inválido: {required}")

    # -------------------------------
    # CARGAR PRECIOS
    # -------------------------------
    if isinstance(precios_o_archivo, str):
        df_precios = cargar_precios(precios_o_archivo)
    else:
        df_precios = precios_o_archivo

    if df_precios is None or df_precios.empty:
        raise ValueError("df_precios inválido")

    # -------------------------------
    # LIMPIEZA BASE
    # -------------------------------
    base = df_resumen.copy()

    base.columns = [str(c).strip() for c in base.columns]

    if "Unidad" not in base.columns:
        base["Unidad"] = ""

    base["Materiales"] = base["Materiales"].astype(str).str.strip()
    base["Unidad"] = base["Unidad"].astype(str).str.strip()

    base["Cantidad"] = pd.to_numeric(
        base["Cantidad"], errors="coerce"
    ).fillna(0.0)

    # -------------------------------
    # NORMALIZACIÓN
    # -------------------------------
    base["Materiales_norm"] = base["Materiales"].map(_norm_txt)
    base["Unidad_norm"] = base["Unidad"].map(_norm_txt)

    # -------------------------------
    # MERGE
    # -------------------------------
    out = base.merge(
        df_precios,
        on=["Materiales_norm", "Unidad_norm"],
        how="left",
    )

    out["Precio Unitario"] = pd.to_numeric(
        out["Precio Unitario"], errors="coerce"
    )

    out["Moneda"] = out["Moneda"].fillna("L")

    # -------------------------------
    # COSTO
    # -------------------------------
    out["Tiene_Precio"] = (
        out["Precio Unitario"].notna()
        & (out["Precio Unitario"] > 0)
    )

    out["Costo"] = pd.NA

    mask = out["Tiene_Precio"]

    out.loc[mask, "Costo"] = (
        out.loc[mask, "Precio Unitario"]
        * out.loc[mask, "Cantidad"]
    ).round(2)

    return out[
        [
            "Materiales",
            "Unidad",
            "Cantidad",
            "Precio Unitario",
            "Costo",
            "Moneda",
            "Tiene_Precio",
        ]
    ]


# =========================================================
# PRECIO DE VENTA (CLIENTE)
# =========================================================
def generar_precios_venta(
    df_costos: pd.DataFrame,
    margen: float = 0.15
) -> pd.DataFrame:

    if df_costos is None or df_costos.empty:
        raise ValueError("df_costos vacío")

    df = df_costos.copy()

    df["Precio Unitario Venta"] = pd.NA
    df["Total Venta"] = pd.NA

    mask = df["Costo"].notna()

    df.loc[mask, "Precio Unitario Venta"] = (
        df.loc[mask, "Costo"].astype(float)
        * (1 + margen)
    ).round(2)

    df.loc[mask, "Total Venta"] = (
        df.loc[mask, "Precio Unitario Venta"].astype(float)
        * df.loc[mask, "Cantidad"].astype(float)
    ).round(2)

    return df[
        [
            "Materiales",
            "Unidad",
            "Cantidad",
            "Precio Unitario Venta",
            "Total Venta",
        ]
    ]
