# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from materiales.auxiliares.materiales_aux import (
    expandir_lista_codigos,
    limpiar_codigo,
)


# ==========================================================
# API PRINCIPAL
# ==========================================================
def normalizar_estructuras(df: pd.DataFrame):

    if df is None or df.empty:
        return (
            pd.DataFrame(columns=["Punto", "Estructura", "Cantidad"]),
            ["Entrada vacía"],
            []
        )

    # ======================================================
    # FORMATO
    # ======================================================
    if _es_formato_largo(df):
        df_base = df.copy()
    else:
        df_base = _convertir_a_largo(df)

    if df_base.empty:
        return df_base, ["No se pudo normalizar"], []

    # ======================================================
    # LIMPIEZA
    # ======================================================
    df_base.columns = df_base.columns.str.strip().str.lower()

    if "punto" not in df_base.columns:
        return df_base, ["Falta columna Punto"], []

    if "codigodeestructura" not in df_base.columns:
        return df_base, ["Falta columna Estructura"], []

    df_base["punto"] = df_base["punto"].astype(str).str.strip()
    df_base["codigodeestructura"] = df_base["codigodeestructura"].astype(str).str.strip()

    # ======================================================
    # AGRUPACIÓN
    # ======================================================
    df_final = (
        df_base
        .groupby(["punto", "codigodeestructura"], as_index=False)
        .size()
        .rename(columns={"size": "cantidad"})
    )

    # ======================================================
    # 🔥 CONTRATO UNIFICADO
    # ======================================================
    df_final = df_final.rename(columns={
        "punto": "Punto",
        "codigodeestructura": "Estructura",
        "cantidad": "Cantidad"
    })

    # ======================================================
    # TIPOS
    # ======================================================
    df_final["Punto"] = df_final["Punto"].astype(str)
    df_final["Estructura"] = df_final["Estructura"].astype(str)
    df_final["Cantidad"] = pd.to_numeric(
        df_final["Cantidad"], errors="coerce"
    ).fillna(0)

    return df_final, [], []


# ==========================================================
# DETECCIÓN DE FORMATO
# ==========================================================
def _es_formato_largo(df: pd.DataFrame) -> bool:
    cols = [c.lower().strip() for c in df.columns]
    return "punto" in cols and "codigodeestructura" in cols


# ==========================================================
# CONVERSIÓN A FORMATO LARGO
# ==========================================================
def _convertir_a_largo(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()
    df.columns = df.columns.str.strip()

    registros = []

    for idx, row in df.iterrows():

        punto = row.get("Punto") or row.get("punto") or f"P-{idx+1}"

        estructura_raw = None

        for col in df.columns:
            if col.lower() in ["estructura", "estructuras", "codigodeestructura"]:
                estructura_raw = row.get(col)
                break

        if estructura_raw is None:
            continue

        lista_codigos = expandir_lista_codigos(estructura_raw)

        for cod in lista_codigos:
            cod = limpiar_codigo(cod)

            if cod:
                registros.append({
                    "punto": str(punto).strip(),
                    "codigodeestructura": cod,
                    "cantidad": 1
                })

    return pd.DataFrame(registros)
