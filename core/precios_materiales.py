# -*- coding: utf-8 -*-
"""
core/precios_materiales.py

Carga precios y construye tabla de costos a partir de df_resumen:
df_resumen: Materiales, Unidad, Cantidad
Salida: df_costos: Materiales, Unidad, Cantidad, Precio Unitario, Costo
"""

from __future__ import annotations
import pandas as pd


def cargar_precios(archivo_materiales: str) -> pd.DataFrame:
    try:
        df = pd.read_excel(archivo_materiales, sheet_name="Materiales")
        df.columns = [str(c).strip() for c in df.columns]

        ren = {}
        for c in df.columns:
            cc = c.lower()
            if "descripción" in cc or "descripcion" in cc:
                ren[c] = "Materiales"
            elif cc.startswith("unidad"):
                ren[c] = "Unidad"
            elif "costo" in cc and "unit" in cc:
                ren[c] = "Precio Unitario"

        df = df.rename(columns=ren)

        # columnas mínimas
        for col in ["Materiales", "Unidad", "Precio Unitario"]:
            if col not in df.columns:
                df[col] = ""

        df["Materiales"] = df["Materiales"].astype(str).str.strip()
        df["Unidad"] = df["Unidad"].astype(str).str.strip()
        df["Precio Unitario"] = pd.to_numeric(
            df["Precio Unitario"], errors="coerce"
        ).fillna(0.0)

        return df[["Materiales", "Unidad", "Precio Unitario"]]

    except Exception as e:
        print("ERROR cargando precios:", e)
        return pd.DataFrame(columns=["Materiales", "Unidad", "Precio Unitario"])



def construir_costos(df_resumen: pd.DataFrame, df_precios: pd.DataFrame) -> pd.DataFrame:
    if df_resumen is None or df_resumen.empty:
        return pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad", "Precio Unitario", "Costo"])

    base = df_resumen.copy()
    base["Materiales"] = base["Materiales"].astype(str).str.strip()
    base["Unidad"] = base["Unidad"].astype(str).str.strip()
    base["Cantidad"] = pd.to_numeric(base["Cantidad"], errors="coerce").fillna(0.0)

    precios = df_precios.copy() if df_precios is not None else pd.DataFrame()
    if precios is None or precios.empty:
        base["Precio Unitario"] = 0.0
    else:
        base = base.merge(precios, on=["Materiales", "Unidad"], how="left")
        base["Precio Unitario"] = pd.to_numeric(base["Precio Unitario"], errors="coerce").fillna(0.0)

    base["Costo"] = (base["Cantidad"] * base["Precio Unitario"]).round(2)
    return base[["Materiales", "Unidad", "Cantidad", "Precio Unitario", "Costo"]]
