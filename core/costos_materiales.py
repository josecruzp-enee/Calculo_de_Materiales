# -*- coding: utf-8 -*-
"""
core/costos_materiales.py
Arma df_costos_materiales cruzando df_resumen con hoja 'precios'.
"""

from __future__ import annotations
import pandas as pd
import unicodedata


def _norm_txt(s: object) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    t = str(s).strip()
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    t = " ".join(t.split())
    return t.upper()


def cargar_precios(archivo_materiales: str) -> pd.DataFrame:
    try:
        df = pd.read_excel(archivo_materiales, sheet_name="precios")
    except Exception:
        return pd.DataFrame(columns=["Materiales", "Unidad", "Precio_Unitario", "Moneda"])

    df.columns = [str(c).strip() for c in df.columns]

    # Asegurar columnas mínimas
    for c in ["Materiales", "Unidad", "Precio_Unitario", "Moneda"]:
        if c not in df.columns:
            df[c] = ""

    # Normalización para match robusto
    df["Materiales_norm"] = df["Materiales"].map(_norm_txt)
    df["Unidad_norm"] = df["Unidad"].map(_norm_txt)

    # Precio a número
    df["Precio_Unitario"] = pd.to_numeric(df["Precio_Unitario"], errors="coerce")

    # Quitar duplicados (si existen)
    df = df.drop_duplicates(subset=["Materiales_norm", "Unidad_norm"], keep="last")

    return df[["Materiales", "Unidad", "Precio_Unitario", "Moneda", "Materiales_norm", "Unidad_norm"]].copy()


def construir_costos_desde_resumen(df_resumen: pd.DataFrame, archivo_materiales: str) -> pd.DataFrame:
    """
    df_resumen debe tener: Materiales, Unidad, Cantidad
    retorna: Materiales, Unidad, Cantidad, Precio_Unitario, Costo_Total, Moneda, Tiene_Precio
    """
    if df_resumen is None or df_resumen.empty:
        return pd.DataFrame(columns=[
            "Materiales", "Unidad", "Cantidad", "Precio_Unitario",
            "Costo_Total", "Moneda", "Tiene_Precio"
        ])

    precios = cargar_precios(archivo_materiales)

    df = df_resumen.copy()
    df.columns = [str(c).strip() for c in df.columns]

    df["Materiales_norm"] = df["Materiales"].map(_norm_txt)
    df["Unidad_norm"] = df["Unidad"].map(_norm_txt)
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0.0)

    if precios is None or precios.empty:
        df["Precio_Unitario"] = pd.NA
        df["Moneda"] = ""
        df["Costo_Total"] = pd.NA
        df["Tiene_Precio"] = False
        return df[["Materiales", "Unidad", "Cantidad", "Precio_Unitario", "Costo_Total", "Moneda", "Tiene_Precio"]]

    dfm = df.merge(
        precios[["Materiales_norm", "Unidad_norm", "Precio_Unitario", "Moneda"]],
        on=["Materiales_norm", "Unidad_norm"],
        how="left",
    )

    dfm["Tiene_Precio"] = dfm["Precio_Unitario"].notna()
    dfm["Costo_Total"] = dfm["Precio_Unitario"] * dfm["Cantidad"]

    return dfm[["Materiales", "Unidad", "Cantidad", "Precio_Unitario", "Costo_Total", "Moneda", "Tiene_Precio"]]
