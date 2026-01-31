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
    """
    Lee precios desde Estructura_datos.xlsx, hoja 'Materiales' (tu tabla maestra).
    Espera columnas tipo:
      - 'DESCRIPCIÓN DE MATERIALES' (o similar)
      - 'Unidad'
      - 'Costo Unitario' (o similar)
      - opcional: 'Moneda'
    """
    try:
        df = pd.read_excel(archivo_materiales, sheet_name="Materiales")
    except Exception:
        return pd.DataFrame(columns=["Materiales", "Unidad", "Precio_Unitario", "Moneda"])

    df.columns = [str(c).strip() for c in df.columns]

    # Mapear nombres reales de tu Excel -> nombres estándar del motor
    ren = {
        "DESCRIPCIÓN DE MATERIALES": "Materiales",
        "DESCRIPCION DE MATERIALES": "Materiales",
        "DESCRIPCIÓN": "Materiales",
        "DESCRIPCION": "Materiales",
        "Costo Unitario": "Precio_Unitario",
        "COSTO UNITARIO": "Precio_Unitario",
        "Costo_Unitario": "Precio_Unitario",
        "COSTO_UNITARIO": "Precio_Unitario",
    }
    df = df.rename(columns=ren)

    # Asegurar columnas mínimas
    for c in ["Materiales", "Unidad", "Precio_Unitario"]:
        if c not in df.columns:
            df[c] = ""

    if "Moneda" not in df.columns:
        # si no la tenés en la tabla, la fijamos (como en tu ejemplo)
        df["Moneda"] = "L"

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
