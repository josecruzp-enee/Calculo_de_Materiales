# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from entradas.normalizar import limpiar_codigo
from materiales.calculos.lector_materiales import leer_hoja_materiales

COLUMNAS_STD = ["Materiales", "Unidad", "Cantidad"]


# ==========================================================
# NORMALIZAR CÓDIGO DE ESTRUCTURA
# ==========================================================
def _normalizar_codigo(estructura: str) -> str:

    estructura = str(estructura or "").strip().upper()

    if not estructura:
        return ""

    estructura = limpiar_codigo(estructura)

    return estructura


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

    # -------------------------
    # NORMALIZAR
    # -------------------------
    estructura = _normalizar_codigo(estructura)

    if not estructura:
        raise ValueError("Estructura vacía")

    # -------------------------
    # VALIDAR CANTIDAD
    # -------------------------
    try:
        cantidad = float(cantidad)
    except Exception:
        raise ValueError(f"Cantidad inválida para {estructura}: {cantidad}")

    if cantidad <= 0:
        raise ValueError(f"Cantidad inválida para {estructura}: {cantidad}")

    # -------------------------
    # VALIDAR HOJA
    # -------------------------
    df_hoja = hojas_base.get(estructura)

    if df_hoja is None or not isinstance(df_hoja, pd.DataFrame):
        raise ValueError(f"Estructura no encontrada o inválida: {estructura}")

    # -------------------------
    # LEER HOJA
    # -------------------------
    try:
        df_filtrado = leer_hoja_materiales(df_hoja, tension)
    except Exception as e:
        raise RuntimeError(f"Error leyendo hoja {estructura}: {e}")

    if df_filtrado is None or df_filtrado.empty:
        raise ValueError(f"Sin materiales para {estructura} @ {tension}")

    df_filtrado = df_filtrado.copy()

    # -------------------------
    # NORMALIZAR COLUMNAS
    # -------------------------
    df_filtrado.columns = [str(c).strip() for c in df_filtrado.columns]

    # -------------------------
    # VALIDAR COLUMNAS
    # -------------------------
    if not set(COLUMNAS_STD).issubset(df_filtrado.columns):
        raise ValueError(
            f"Formato inválido en hoja {estructura}: {list(df_filtrado.columns)}"
        )

    # -------------------------
    # NORMALIZAR CANTIDADES
    # -------------------------
    df_filtrado["Cantidad"] = pd.to_numeric(
        df_filtrado["Cantidad"], errors="coerce"
    ).fillna(0.0)

    df_filtrado["Cantidad"] *= cantidad

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

    # -------------------------
    # VALIDACIÓN INPUT
    # -------------------------
    if df_estructuras is None or df_estructuras.empty:
        return pd.DataFrame(columns=["Punto", "Materiales", "Unidad", "Cantidad"])

    resultados = []
    errores = []

    # -------------------------
    # LOOP PRINCIPAL
    # -------------------------
    for row in df_estructuras.to_dict("records"):

        punto = str(row.get("Punto") or row.get("punto") or "").strip() or "General"

        estructura = (
            row.get("codigodeestructura")
            or row.get("Estructura")
            or ""
        )

        # -------------------------
        # VALIDAR CANTIDAD
        # -------------------------
        try:
            cantidad = float(row.get("cantidad", 1))
        except Exception:
            cantidad = 1.0

        if cantidad <= 0:
            continue

        if not estructura:
            continue

        # -------------------------
        # CALCULAR
        # -------------------------
        try:
            df_mat = calcular_materiales_estructura(
                hojas_base=hojas_base,
                estructura=estructura,
                cantidad=1,
                tension=tension,
                calibre_mt=calibre_mt,
                tabla_conectores_mt=tabla_conectores_mt,
            )

            df_mat = df_mat.copy()
            df_mat["Punto"] = punto

            resultados.append(df_mat)

        except Exception as e:
            errores.append(f"{estructura}: {e}")

    # -------------------------
    # VALIDACIÓN FINAL
    # -------------------------
    if not resultados:
        raise ValueError(
            f"No se pudo calcular ningún material. "
            f"Errores: {errores[:5]}"
        )

    # -------------------------
    # CONSOLIDACIÓN
    # -------------------------
    df_final = pd.concat(resultados, ignore_index=True)

    df_final = (
        df_final
        .groupby(["Punto", "Materiales", "Unidad"], as_index=False)["Cantidad"]
        .sum()
        .sort_values(["Punto", "Materiales"])
        .reset_index(drop=True)
    )

    return df_final[["Punto", "Materiales", "Unidad", "Cantidad"]]

# ==========================================================
# 🔥 NUEVO: MATERIALES POR ESTRUCTURA
# ==========================================================
def calcular_materiales_por_estructura(
    hojas_base,
    df_estructuras,
    tension,
    calibre_mt=None,
    tabla_conectores_mt=None,
):

    if df_estructuras is None or df_estructuras.empty:
        return {}

    resultado = {}

    for row in df_estructuras.to_dict("records"):

        estructura = (
            row.get("codigodeestructura")
            or row.get("Estructura")
            or ""
        )

        try:
            cantidad = float(row.get("cantidad", row.get("Cantidad", 1)))
        except Exception:
            cantidad = 1.0

        if cantidad <= 0 or not estructura:
            continue

        try:
            df_mat = calcular_materiales_estructura(
                hojas_base=hojas_base,
                estructura=estructura,
                cantidad=cantidad,
                tension=tension,
                calibre_mt=calibre_mt,
                tabla_conectores_mt=tabla_conectores_mt,
            )

            cod = _normalizar_codigo(estructura)

            if cod in resultado:
                resultado[cod] = pd.concat([resultado[cod], df_mat])
            else:
                resultado[cod] = df_mat

        except Exception:
            continue

    # consolidar cada estructura
    for cod in resultado:
        df = resultado[cod]

        resultado[cod] = (
            df.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"]
            .sum()
        )

    return resultado
