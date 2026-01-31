# -*- coding: utf-8 -*-
"""
core/costos_materiales.py

Este módulo es el contrato oficial para costos.

El servicio importa:
  - cargar_tabla_precios(archivo_materiales) -> DataFrame precios
  - calcular_costos_desde_resumen(df_resumen, precios_o_archivo) -> DataFrame costos

Lee hoja: 'precios'
Columnas esperadas (flexibles): Materiales, Unidad, Precio Unitario, Moneda (opcional)

Salida df_costos:
  Materiales, Unidad, Cantidad, Precio Unitario, Costo, Moneda, Tiene_Precio
"""

from __future__ import annotations

import pandas as pd
import unicodedata


# -------------------------
# Normalización robusta
# -------------------------
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


# -------------------------
# API esperada por servicios
# -------------------------
def cargar_tabla_precios(archivo_materiales: str) -> pd.DataFrame:
    """
    Lee hoja 'precios' del Excel.
    Retorna DataFrame con:
      Materiales, Unidad, Precio Unitario, Moneda, Materiales_norm, Unidad_norm
    """
    try:
        df = pd.read_excel(archivo_materiales, sheet_name="precios")
    except Exception:
        return pd.DataFrame(
            columns=["Materiales", "Unidad", "Precio Unitario", "Moneda", "Materiales_norm", "Unidad_norm"]
        )

    df.columns = [str(c).strip() for c in df.columns]

    # Normalizar nombres de columnas a estándar
    ren = {}
    for c in df.columns:
        cc = c.lower().strip()
        if cc.startswith("material"):
            ren[c] = "Materiales"
        elif cc.startswith("unidad"):
            ren[c] = "Unidad"
        elif "precio" in cc or "costo" in cc:
            ren[c] = "Precio Unitario"
        elif "moneda" in cc:
            ren[c] = "Moneda"

    df = df.rename(columns=ren)

    # Asegurar mínimas
    for col in ["Materiales", "Unidad", "Precio Unitario"]:
        if col not in df.columns:
            df[col] = ""

    if "Moneda" not in df.columns:
        df["Moneda"] = ""

    df["Materiales"] = df["Materiales"].astype(str).str.strip()
    df["Unidad"] = df["Unidad"].astype(str).str.strip()
    df["Precio Unitario"] = pd.to_numeric(df["Precio Unitario"], errors="coerce")

    # Normalización para match robusto
    df["Materiales_norm"] = df["Materiales"].map(_norm_txt)
    df["Unidad_norm"] = df["Unidad"].map(_norm_txt)

    # quitar duplicados por material+unidad normalizados
    df = df.drop_duplicates(subset=["Materiales_norm", "Unidad_norm"], keep="last")

    return df[
        ["Materiales", "Unidad", "Precio Unitario", "Moneda", "Materiales_norm", "Unidad_norm"]
    ].copy()


def calcular_costos_desde_resumen(df_resumen: pd.DataFrame, precios_o_archivo) -> pd.DataFrame:
    """
    Construye df_costos a partir de df_resumen (Materiales, Unidad, Cantidad).

    precios_o_archivo puede ser:
      A) DataFrame de precios (salida de cargar_tabla_precios)
      B) str ruta del archivo_materiales (para autoleer precios)

    Retorna:
      Materiales, Unidad, Cantidad, Precio Unitario, Costo, Moneda, Tiene_Precio
    """
    if df_resumen is None or df_resumen.empty:
        return pd.DataFrame(
            columns=["Materiales", "Unidad", "Cantidad", "Precio Unitario", "Costo", "Moneda", "Tiene_Precio"]
        )

    # Obtener tabla de precios
    if isinstance(precios_o_archivo, str):
        df_precios = cargar_tabla_precios(precios_o_archivo)
    else:
        df_precios = precios_o_archivo

    base = df_resumen.copy()
    base.columns = [str(c).strip() for c in base.columns]

    for col in ["Materiales", "Unidad", "Cantidad"]:
        if col not in base.columns:
            base[col] = ""

    base["Materiales"] = base["Materiales"].astype(str).str.strip()
    base["Unidad"] = base["Unidad"].astype(str).str.strip()
    base["Cantidad"] = pd.to_numeric(base["Cantidad"], errors="coerce").fillna(0.0)

    base["Materiales_norm"] = base["Materiales"].map(_norm_txt)
    base["Unidad_norm"] = base["Unidad"].map(_norm_txt)

    if df_precios is None or getattr(df_precios, "empty", True):
        base["Precio Unitario"] = pd.NA
        base["Moneda"] = ""
        base["Tiene_Precio"] = False
        base["Costo"] = pd.NA
        return base[["Materiales", "Unidad", "Cantidad", "Precio Unitario", "Costo", "Moneda", "Tiene_Precio"]]

    precios = df_precios.copy()
    # asegurar cols
    for col in ["Precio Unitario", "Moneda", "Materiales_norm", "Unidad_norm"]:
        if col not in precios.columns:
            precios[col] = ""

    out = base.merge(
        precios[["Materiales_norm", "Unidad_norm", "Precio Unitario", "Moneda"]],
        on=["Materiales_norm", "Unidad_norm"],
        how="left",
    )

    out["Tiene_Precio"] = out["Precio Unitario"].notna()
    out["Costo"] = out["Precio Unitario"] * out["Cantidad"]

    return out[["Materiales", "Unidad", "Cantidad", "Precio Unitario", "Costo", "Moneda", "Tiene_Precio"]]
