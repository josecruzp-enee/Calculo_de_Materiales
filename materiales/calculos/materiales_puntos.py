# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from collections import Counter

from entradas.normalizar import expandir_lista_codigos, limpiar_codigo
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
# CONTEO (FIX CRÍTICO)
# ==========================================================
def extraer_conteo_estructuras(df_estructuras):

    if df_estructuras is None or df_estructuras.empty:
        return Counter(), {}

    estructuras_limpias = []
    estructuras_por_punto = {}

    for _, row in df_estructuras.iterrows():

        punto = str(row.get("punto") or "").strip() or "Punto"

        # 🔥 FIX: usar columna correcta
        estructura = row.get("codigodeestructura")

        if not estructura:
            continue

        estructura = limpiar_codigo(estructura)

        estructuras_limpias.append(estructura)

        estructuras_por_punto.setdefault(punto, []).append(estructura)

    conteo = Counter(estructuras_limpias)

    _debug("conteo_total", dict(conteo))

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
# MATERIAL TOTAL (FIX + DEBUG PRO)
# ==========================================================
def calcular_materiales_por_punto(
    hojas_base,
    df_estructuras,
    tension,
    calibre_mt=None,
    tabla_conectores_mt=None,
):

    conteo, _ = extraer_conteo_estructuras(df_estructuras)

    _check("conteo_no_vacio", len(conteo) > 0, conteo)

    if not conteo:
        return pd.DataFrame(columns=COLUMNAS_STD)

    resultados = []
    errores = []

    for estructura, cant in conteo.items():

        try:
            df_mat = calcular_materiales_estructura(
                hojas_base=hojas_base,
                estructura=estructura,
                cant=cant,
                tension=tension,
                calibre_mt=calibre_mt,
                tabla_conectores_mt=tabla_conectores_mt,
            )

            _debug(f"estructura_ok::{estructura}", len(df_mat))

            resultados.append(df_mat)

        except Exception as e:
            errores.append(f"{estructura}: {e}")
            _debug(f"estructura_error::{estructura}", str(e))

    _debug("errores_estructuras", errores)

    _check("sin_errores_criticos", len(resultados) > 0, errores)

    if not resultados:
        raise ValueError(f"No se pudo calcular ninguna estructura: {errores}")

    df_final = pd.concat(resultados, ignore_index=True)

    df_final = (
        df_final
        .groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"]
        .sum()
    )

    _debug("df_final", df_final)

    return df_final[COLUMNAS_STD]
