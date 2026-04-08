# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from entradas.normalizar import limpiar_codigo
from materiales.calculos.lector_materiales import leer_hoja_materiales

COLUMNAS_STD = ["Materiales", "Unidad", "Cantidad"]


# ==========================================================
# MATERIAL POR ESTRUCTURA
# ==========================================================
def calcular_materiales_estructura(
    hojas_base,
    estructura,
    cantidad,
    tension,
    calibre_mt=None,
    tabla_conectores_mt=None,
):

    estructura = str(estructura or "").strip().upper()

    if not estructura:
        raise ValueError("Estructura vacía")

    if cantidad is None or float(cantidad) <= 0:
        raise ValueError(f"Cantidad inválida para {estructura}: {cantidad}")

    df_hoja = hojas_base.get(estructura)

    if df_hoja is None:
        raise ValueError(f"Estructura no encontrada: {estructura}")

    df_filtrado = leer_hoja_materiales(df_hoja, tension)

    if df_filtrado is None or df_filtrado.empty:
        raise ValueError(f"Sin materiales para {estructura} @ {tension}")

    df_filtrado = df_filtrado.copy()

    df_filtrado["Cantidad"] = pd.to_numeric(
        df_filtrado["Cantidad"], errors="coerce"
    ).fillna(0)

    df_filtrado["Cantidad"] *= float(cantidad)

    return df_filtrado[COLUMNAS_STD]


# ==========================================================
# FUNCIÓN PRINCIPAL: POR PUNTO
# ==========================================================
def calcular_materiales_por_punto(
    hojas_base,
    df_estructuras,
    tension,
    calibre_mt=None,
    tabla_conectores_mt=None,
):

    if df_estructuras is None or df_estructuras.empty:
        return pd.DataFrame(columns=["Punto", "Materiales", "Unidad", "Cantidad"])

    resultados = []

    for _, row in df_estructuras.iterrows():

        punto = str(row.get("Punto") or row.get("punto") or "").strip() or "General"
        estructura = row.get("codigodeestructura") or row.get("Estructura")
        cantidad = row.get("cantidad", 1)

        if not estructura:
            continue

        df_mat = calcular_materiales_estructura(
            hojas_base=hojas_base,
            estructura=estructura,
            cantidad=cantidad,
            tension=tension,
            calibre_mt=calibre_mt,
            tabla_conectores_mt=tabla_conectores_mt,
        )

        df_mat = df_mat.copy()
        df_mat["Punto"] = punto

        resultados.append(df_mat)

    if not resultados:
        raise ValueError("No se pudo calcular ningún material")

    df_final = pd.concat(resultados, ignore_index=True)

    # 🔥 consolidación por punto
    df_final = (
        df_final
        .groupby(["Punto", "Materiales", "Unidad"], as_index=False)["Cantidad"]
        .sum()
    )

    return df_final[["Punto", "Materiales", "Unidad", "Cantidad"]]
