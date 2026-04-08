# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from collections import Counter

from entradas.normalizar import expandir_lista_codigos, limpiar_codigo
from materiales.calculos.lector_materiales import leer_hoja_materiales

COLUMNAS_STD = ["Materiales", "Unidad", "Cantidad"]


# ==========================================================
# VALIDADOR FUERTE
# ==========================================================
def _validar_df(df: pd.DataFrame) -> None:

    if df is None:
        raise ValueError("DataFrame es None")

    if not isinstance(df, pd.DataFrame):
        raise TypeError("Se esperaba DataFrame")

    if df.empty:
        return

    if not set(COLUMNAS_STD).issubset(df.columns):
        raise ValueError(f"Formato inválido: {df.columns}")

    if df["Materiales"].isna().any():
        raise ValueError("Materiales contiene valores nulos")

    if df["Unidad"].isna().any():
        raise ValueError("Unidad contiene valores nulos")

    if (pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0) < 0).any():
        raise ValueError("Cantidad contiene valores negativos")


# ==========================================================
# CONTEO DE ESTRUCTURAS
# ==========================================================
def extraer_conteo_estructuras(df_estructuras):

    if df_estructuras is None or df_estructuras.empty:
        return Counter(), {}

    estructuras_limpias = []
    estructuras_por_punto = {}

    for _, row in df_estructuras.iterrows():

        punto = str(row.get("Punto") or "").strip() or "Punto"
        estructuras_raw = str(row.get("Estructura") or "").strip()

        if not estructuras_raw:
            estructuras_por_punto[punto] = []
            continue

        codigos = expandir_lista_codigos(estructuras_raw)

        lista_limpia = []

        for c in codigos:

            c = limpiar_codigo(c)

            if not c:
                continue

            estructuras_limpias.append(c)
            lista_limpia.append(c)

        estructuras_por_punto[punto] = lista_limpia

    conteo = Counter(estructuras_limpias)

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

    cant = int(cant)

    df_hoja = hojas_base.get(estructura)

    if df_hoja is None:
        raise ValueError(f"Estructura no encontrada en base de datos: {estructura}")

    if df_hoja.empty:
        raise ValueError(f"Hoja vacía para estructura: {estructura}")

    df_filtrado = leer_hoja_materiales(df_hoja, tension)

    if df_filtrado is None or df_filtrado.empty:
        raise ValueError(
            f"No hay materiales para estructura {estructura} en tensión {tension}"
        )

    _validar_df(df_filtrado)

    df_filtrado = df_filtrado.copy()

    df_filtrado["Materiales"] = df_filtrado["Materiales"].astype(str).str.strip()
    df_filtrado["Unidad"] = df_filtrado["Unidad"].astype(str).str.strip()

    df_filtrado["Cantidad"] = pd.to_numeric(
        df_filtrado["Cantidad"], errors="coerce"
    )

    if df_filtrado["Cantidad"].isna().any():
        raise ValueError(f"Cantidad inválida en estructura {estructura}")

    df_filtrado["Cantidad"] *= float(cant)

    df_filtrado = (
        df_filtrado
        .groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"]
        .sum()
    )

    from ayuda.debug import debug_guardar

    debug_guardar(f"estructura_{estructura}", estructura)
    debug_guardar(f"df_estructura_{estructura}", df_filtrado)

    return df_filtrado[COLUMNAS_STD]


# ==========================================================
# MATERIAL TOTAL DEL PROYECTO
# ==========================================================
def calcular_materiales_por_punto(
    hojas_base,
    df_estructuras,
    tension,
    calibre_mt=None,
    tabla_conectores_mt=None,
):

    conteo, _ = extraer_conteo_estructuras(df_estructuras)

    if not conteo:
        return pd.DataFrame(columns=COLUMNAS_STD)

    resultados = []

    for estructura, cant in conteo.items():

        df_mat = calcular_materiales_estructura(
            hojas_base=hojas_base,
            estructura=estructura,
            cant=cant,
            tension=tension,
            calibre_mt=calibre_mt,
            tabla_conectores_mt=tabla_conectores_mt,
        )

        resultados.append(df_mat)

    df_final = pd.concat(resultados, ignore_index=True)

    _validar_df(df_final)

    df_final = (
        df_final
        .groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"]
        .sum()
    )

    return df_final[COLUMNAS_STD]
