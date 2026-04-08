# -*- coding: utf-8 -*-
"""
calculo_estructuras.py

Genera:
1) Conteo global de estructuras
2) Descripción de estructuras por punto
"""

from __future__ import annotations

import pandas as pd
from collections import Counter
from entradas.normalizar import limpiar_codigo


# ==========================================================
# 🔧 NORMALIZACIÓN
# ==========================================================

def _normalizar_df(df: pd.DataFrame) -> pd.DataFrame:

    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    return df


def _obtener_columna(df, opciones):

    for col in df.columns:
        c = col.lower().replace(" ", "")
        if any(op in c for op in opciones):
            return col

    return None


# ==========================================================
# 🔥 EXTRACCIÓN BASE
# ==========================================================

def _extraer_datos(df_estructuras):

    df = _normalizar_df(df_estructuras)

    if df is None or df.empty:
        return []

    col_est = _obtener_columna(df, ["codigoestructura", "estructura"])
    col_punto = _obtener_columna(df, ["punto"])
    col_cant = _obtener_columna(df, ["cantidad", "cant"])

    if col_est is None:
        raise ValueError(f"No se encontró columna de estructuras: {list(df.columns)}")

    registros = []

    for _, row in df.iterrows():

        estructura = row.get(col_est)
        if not estructura:
            continue

        estructura = limpiar_codigo(estructura)

        punto = row.get(col_punto)
        punto = str(punto).strip() if punto else "General"

        cantidad = row.get(col_cant, 1)
        try:
            cantidad = int(float(cantidad))
        except:
            cantidad = 1

        registros.append({
            "Punto": punto,
            "Estructura": estructura,
            "Cantidad": cantidad
        })

    return registros


# ==========================================================
# 📊 GLOBAL
# ==========================================================

def calcular_estructuras_global(df_estructuras) -> pd.DataFrame:

    registros = _extraer_datos(df_estructuras)

    if not registros:
        return pd.DataFrame(columns=["Estructura", "Cantidad"])

    conteo = Counter()

    for r in registros:
        conteo[r["Estructura"]] += r["Cantidad"]

    data = [
        {"Estructura": est, "Cantidad": cant}
        for est, cant in conteo.items()
    ]

    return pd.DataFrame(data)


# ==========================================================
# 📍 POR PUNTO
# ==========================================================

def calcular_estructuras_por_punto(df_estructuras) -> pd.DataFrame:

    registros = _extraer_datos(df_estructuras)

    if not registros:
        return pd.DataFrame(columns=["Punto", "Estructura", "Cantidad"])

    df = pd.DataFrame(registros)

    df_agr = (
        df
        .groupby(["Punto", "Estructura"], as_index=False)["Cantidad"]
        .sum()
    )

    return df_agr


# ==========================================================
# 🧠 DESCRIPCIÓN POR PUNTO (CLAVE)
# ==========================================================

def generar_descripcion_por_punto(df_estructuras) -> dict:

    df = calcular_estructuras_por_punto(df_estructuras)

    if df.empty:
        return {}

    resultado = {}

    for punto in sorted(df["Punto"].unique()):

        df_p = df[df["Punto"] == punto]

        partes = []

        for _, row in df_p.iterrows():
            est = row["Estructura"]
            cant = int(row["Cantidad"])

            partes.append(f"{est} ({cant})")

        resultado[punto] = ", ".join(partes)

    return resultado


# ==========================================================
# 🚀 FUNCIÓN PRINCIPAL
# ==========================================================

def calcular_estructuras_proyecto(df_estructuras):

    df_global = calcular_estructuras_global(df_estructuras)
    df_por_punto = calcular_estructuras_por_punto(df_estructuras)
    descripcion = generar_descripcion_por_punto(df_estructuras)

    return {
        "df_estructuras": df_global,
        "df_estructuras_por_punto": df_por_punto,
        "descripcion_por_punto": descripcion
    }
