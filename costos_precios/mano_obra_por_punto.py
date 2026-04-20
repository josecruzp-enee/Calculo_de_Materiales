# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd


# ==========================================================
# CONFIGURACIÓN BASE (BIBLIOTECA DE EJECUCIÓN)
# ==========================================================
COSTOS_BASE = {
    "poste": 2000,
    "primario": 1500,
    "secundario": 1000,
    "luminaria": 500,
    "retenida": 800,
}

FACTOR_FASES = {
    "A-I": 1.0,
    "A-II": 1.3,
    "A-III": 1.6,
}

FACTOR_COMPLEJIDAD = {
    "PASO": 1.0,
    "ANGULO": 1.2,
    "DOBLE": 1.4,
    "REMATE": 1.6,
}


# ==========================================================
# PRECIO POR ESTRUCTURA
# ==========================================================
def _precio_estructura(estructura: str) -> float:

    # =========================
    # POSTE
    # =========================
    if estructura.startswith("PC"):
        return COSTOS_BASE["poste"]

    # =========================
    # PRIMARIO
    # =========================
    if estructura.startswith("A-"):

        if estructura.startswith("A-III"):
            f_fase = FACTOR_FASES["A-III"]
        elif estructura.startswith("A-II"):
            f_fase = FACTOR_FASES["A-II"]
        else:
            f_fase = FACTOR_FASES["A-I"]

        if "REM" in estructura:
            f_comp = FACTOR_COMPLEJIDAD["REMATE"]
        elif "DOB" in estructura:
            f_comp = FACTOR_COMPLEJIDAD["DOBLE"]
        else:
            f_comp = FACTOR_COMPLEJIDAD["PASO"]

        return COSTOS_BASE["primario"] * f_fase * f_comp

    # =========================
    # SECUNDARIO
    # =========================
    if estructura.startswith("B-"):
        return COSTOS_BASE["secundario"]

    # =========================
    # LUMINARIA
    # =========================
    if estructura.startswith("LL"):
        return COSTOS_BASE["luminaria"]

    # =========================
    # RETENIDAS
    # =========================
    if estructura.startswith("R-"):
        return COSTOS_BASE["retenida"]

    # =========================
    # 🔥 TIERRA (CT-N)
    # =========================
    if estructura.startswith("CT"):
        return 500  # ajustable

    # =========================
    # 🔥 TRANSFORMADOR (TS)
    # =========================
    if estructura.startswith("TS"):

        PRECIOS_TRANSFORMADOR = {
            "TS-25KVA": 8000,
            "TS-37.5KVA": 12000,
            "TS-50KVA": 15000,
        }

        if estructura in PRECIOS_TRANSFORMADOR:
            return PRECIOS_TRANSFORMADOR[estructura] * 0.5

        return 2000  # fallback si no está en diccionario

    # =========================
    # OTROS
    # =========================
    return 0

# ==========================================================
# DETALLE POR PUNTO
# ==========================================================
def calcular_detalle_mano_obra(df_estructuras_por_punto: pd.DataFrame) -> pd.DataFrame:

    if df_estructuras_por_punto is None or df_estructuras_por_punto.empty:
        return pd.DataFrame(columns=["Punto", "Estructura", "Cantidad", "Precio", "Subtotal"])

    filas = []

    for _, row in df_estructuras_por_punto.iterrows():

        punto = row["Punto"]
        estructura = row["Estructura"]
        cantidad = int(row["Cantidad"])

        precio = _precio_estructura(estructura)
        subtotal = precio * cantidad

        filas.append({
            "Punto": punto,
            "Estructura": estructura,
            "Cantidad": cantidad,
            "Precio": round(precio, 2),
            "Subtotal": round(subtotal, 2),
        })

    return pd.DataFrame(filas)


# ==========================================================
# TOTAL POR PUNTO
# ==========================================================
def calcular_totales_por_punto(df_detalle: pd.DataFrame) -> pd.DataFrame:

    if df_detalle is None or df_detalle.empty:
        return pd.DataFrame(columns=["Punto", "TOTAL_PUNTO"])

    return (
        df_detalle
        .groupby("Punto", as_index=False)["Subtotal"]
        .sum()
        .rename(columns={"Subtotal": "TOTAL_PUNTO"})
    )


# ==========================================================
# FUNCIÓN PRINCIPAL (INTEGRADA)
# ==========================================================
def calcular_mano_obra_proyecto(df_estructuras_por_punto: pd.DataFrame):

    df_detalle = calcular_detalle_mano_obra(df_estructuras_por_punto)
    df_totales = calcular_totales_por_punto(df_detalle)

    df_detalle = df_detalle.sort_values(["Punto", "Estructura"])
    df_totales = df_totales.sort_values("Punto")

    return {
        "df_detalle": df_detalle,
        "df_totales": df_totales,
    }
