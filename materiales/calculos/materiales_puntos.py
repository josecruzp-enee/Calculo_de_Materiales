# -*- coding: utf-8 -*-

from __future__ import annotations
import pandas as pd
from collections import Counter

from materiales.auxiliares.materiales_aux import limpiar_codigo, expandir_lista_codigos
from materiales.auxiliares.lector_materiales import leer_hoja_materiales

COLUMNAS_STD = ["Materiales", "Unidad", "Cantidad"]


# ==========================================================
# VALIDADOR
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


# ==========================================================
# NORMALIZACIÓN DE ESTRUCTURAS (🔥 CLAVE)
# ==========================================================
def _normalizar_estructura(e: str) -> str | None:

    if not e:
        return None

    for parte in expandir_lista_codigos(e):

        codigo, _ = limpiar_codigo(parte)

        if codigo:
            return str(codigo).strip().upper()

    return None


# ==========================================================
# CONTEO DE ESTRUCTURAS
# ==========================================================
def extraer_conteo_estructuras(df_estructuras):

    if df_estructuras is None or df_estructuras.empty:
        return Counter(), {}

    estructuras_limpias = []
    estructuras_por_punto = {}

    for _, row in df_estructuras.iterrows():

        punto = row.get("Punto", "Punto")

        lista = str(row.get("Estructuras", "")).split(";")

        lista_limpia = []

        for e in lista:

            codigo = _normalizar_estructura(e)

            if codigo:
                estructuras_limpias.append(codigo)
                lista_limpia.append(codigo)

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

    cant = max(int(cant or 1), 1)

    # 🔥 NORMALIZAR CLAVE
    estructura = str(estructura).strip().upper()

    df_hoja = hojas_base.get(estructura)

    if df_hoja is None or df_hoja.empty:
        return pd.DataFrame(columns=COLUMNAS_STD)

    df_filtrado = leer_hoja_materiales(df_hoja, tension)

    if df_filtrado is None or df_filtrado.empty:
        return pd.DataFrame(columns=COLUMNAS_STD)

    _validar_df(df_filtrado)

    df_filtrado = df_filtrado.copy()

    df_filtrado["Materiales"] = df_filtrado["Materiales"].astype(str).str.strip()
    df_filtrado["Unidad"] = df_filtrado["Unidad"].astype(str).str.strip()
    df_filtrado["Cantidad"] = pd.to_numeric(
        df_filtrado["Cantidad"], errors="coerce"
    ).fillna(0)

    # multiplicar por cantidad de estructuras
    df_filtrado["Cantidad"] *= float(cant)

    # consolidar por estructura
    df_filtrado = (
        df_filtrado
        .groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"]
        .sum()
    )

    return df_filtrado[COLUMNAS_STD]


# ==========================================================
# MATERIAL POR PROYECTO
# ==========================================================
def calcular_materiales_por_punto(
    hojas_base,
    df_estructuras,
    tension,
    calibre_mt=None,
    tabla_conectores_mt=None,
):

    conteo, _ = extraer_conteo_estructuras(df_estructuras)

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

        if df_mat is not None and not df_mat.empty:
            resultados.append(df_mat)

    if not resultados:
        return pd.DataFrame(columns=COLUMNAS_STD)

    df_final = pd.concat(resultados, ignore_index=True)

    _validar_df(df_final)

    return df_final[COLUMNAS_STD]
