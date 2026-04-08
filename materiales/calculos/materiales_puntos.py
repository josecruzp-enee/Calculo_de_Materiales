# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from collections import Counter

from entradas.normalizar import limpiar_codigo
from materiales.calculos.lector_materiales import leer_hoja_materiales
from ayuda.debug import debug_guardar

COLUMNAS_STD = ["Materiales", "Unidad", "Cantidad"]


# ==========================================================
# DEBUG HELPERS
# ==========================================================
def _debug(nombre, valor):
    debug_guardar(f"PUNTOS::{nombre}", valor)


def _check(nombre, cond, detalle=None):
    debug_guardar(f"CHECK::PUNTOS::{nombre}", {
        "ok": bool(cond),
        "detalle": str(detalle)[:200]
    })


# ==========================================================
# VALIDADOR
# ==========================================================
def _validar_df(df: pd.DataFrame):

    if df is None:
        raise ValueError("DataFrame es None")

    if not isinstance(df, pd.DataFrame):
        raise TypeError("Se esperaba DataFrame")

    if df.empty:
        return

    if not set(COLUMNAS_STD).issubset(df.columns):
        raise ValueError(f"Formato inválido: {df.columns}")


# ==========================================================
# 🔥 CONTEO CORREGIDO (CLAVE)
# ==========================================================
def extraer_conteo_estructuras(df_estructuras):

    if df_estructuras is None or df_estructuras.empty:
        return Counter(), {}

    estructuras_limpias = []
    estructuras_por_punto = {}

    for _, row in df_estructuras.iterrows():

        # ✅ FIX: leer correctamente Punto
        punto = str(
            row.get("Punto") or row.get("punto") or ""
        ).strip() or "General"

        # ✅ estructura
        estructura = row.get("codigodeestructura") or row.get("Estructura")

        if not estructura:
            continue

        estructura = limpiar_codigo(estructura)

        estructuras_limpias.append(estructura)

        # ✅ mantener relación por punto
        estructuras_por_punto.setdefault(punto, []).append(estructura)

    conteo = Counter(estructuras_limpias)

    _debug("conteo_total", dict(conteo))
    _debug("estructuras_por_punto", estructuras_por_punto)

    return conteo, estructuras_por_punto


# ==========================================================
# MATERIAL POR ESTRUCTURA
# ==========================================================
def calcular_materiales_estructura(
    hojas_base,
    estructura,
    cant,
    tension,
    calibre_mt=None,
    tabla_conectores_mt=None,
):

    estructura = str(estructura or "").strip().upper()

    if not estructura:
        raise ValueError("Estructura vacía")

    if cant is None or float(cant) <= 0:
        raise ValueError(f"Cantidad inválida para {estructura}: {cant}")

    df_hoja = hojas_base.get(estructura)

    _debug(f"estructura_busqueda::{estructura}", df_hoja is not None)

    if df_hoja is None:
        raise ValueError(f"Estructura no encontrada en base: {estructura}")

    df_filtrado = leer_hoja_materiales(df_hoja, tension)

    if df_filtrado is None or df_filtrado.empty:
        raise ValueError(f"Sin materiales para {estructura} @ {tension}")

    df_filtrado = df_filtrado.copy()

    df_filtrado["Cantidad"] = pd.to_numeric(
        df_filtrado["Cantidad"], errors="coerce"
    ).fillna(0)

    df_filtrado["Cantidad"] *= float(cant)

    return df_filtrado[COLUMNAS_STD]


# ==========================================================
# 🔥 MATERIAL POR PUNTO
# ==========================================================
def calcular_materiales_por_punto(
    hojas_base,
    df_estructuras,
    tension,
    calibre_mt=None,
    tabla_conectores_mt=None,
):

    _, estructuras_por_punto = extraer_conteo_estructuras(df_estructuras)

    if not estructuras_por_punto:
        return pd.DataFrame(columns=["Punto", "Materiales", "Unidad", "Cantidad"])

    resultados = []
    errores = []

    for punto, estructuras in estructuras_por_punto.items():

        for estructura in estructuras:

            try:
                df_mat = calcular_materiales_estructura(
                    hojas_base=hojas_base,
                    estructura=estructura,
                    cant=1,
                    tension=tension,
                    calibre_mt=calibre_mt,
                    tabla_conectores_mt=tabla_conectores_mt,
                )

                df_mat = df_mat.copy()
                df_mat["Punto"] = punto

                resultados.append(df_mat)

            except Exception as e:
                errores.append(f"{estructura}: {e}")
                _debug(f"estructura_error::{estructura}", str(e))

    if not resultados:
        raise ValueError(f"No se pudo calcular ninguna estructura: {errores}")

    df_final = pd.concat(resultados, ignore_index=True)

    df_final = (
        df_final
        .groupby(["Punto", "Materiales", "Unidad"], as_index=False)["Cantidad"]
        .sum()
    )

    return df_final[["Punto", "Materiales", "Unidad", "Cantidad"]]
