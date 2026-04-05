# -*- coding: utf-8 -*-

from __future__ import annotations

import pandas as pd
from collections import Counter

from materiales.auxiliares.materiales_aux import limpiar_codigo, expandir_lista_codigos
from entradas.excel_legacy import extraer_estructuras_proyectadas

# ⚠️ PENDIENTE: mover a materiales/reglas/
# from materiales.reglas.conectores_mt import reemplazar_solo_yc25a25_mt

from materiales.auxiliares.lector_materiales import leer_hoja_materiales


# ==========================================================
# CONSTANTES
# ==========================================================
COLUMNAS_STD = ["Materiales", "Unidad", "Cantidad"]


# ==========================================================
# VALIDADOR INTERNO
# ==========================================================
def _validar_df(df: pd.DataFrame) -> None:
    if df is None:
        raise ValueError("DataFrame es None")

    if not isinstance(df, pd.DataFrame):
        raise TypeError("Se esperaba DataFrame")

    if df.empty:
        return

    cols = set(df.columns)
    esperadas = set(COLUMNAS_STD)

    if not esperadas.issubset(cols):
        raise ValueError(f"Formato inválido: {df.columns}")


# ==========================================================
# CONTEO DE ESTRUCTURAS
# ==========================================================
def extraer_conteo_estructuras(df_estructuras):

    estructuras_proyectadas, estructuras_por_punto = extraer_estructuras_proyectadas(df_estructuras)

    estructuras_limpias = []

    for e in estructuras_proyectadas:
        for parte in expandir_lista_codigos(e):
            codigo, _ = limpiar_codigo(parte)
            if codigo:
                estructuras_limpias.append(str(codigo).strip().upper())

    valores_invalidos = {"", "SELECCIONAR", "ESTRUCTURA", "PUNTO", "N/A", "NONE", "0", "1", "2", "3"}

    estructuras_filtradas = [
        e for e in estructuras_limpias
        if e not in valores_invalidos
    ]

    conteo = Counter(estructuras_filtradas)

    estructuras_por_punto_filtrado = {}

    for punto, lista in estructuras_por_punto.items():
        estructuras_validas = []

        for x in lista:
            s = str(x).strip().upper()

            if s and s not in valores_invalidos:
                estructuras_validas.append(s)

        estructuras_por_punto_filtrado[punto] = estructuras_validas

    return conteo, estructuras_por_punto_filtrado


# ==========================================================
# MATERIAL POR ESTRUCTURA
# ==========================================================
def calcular_materiales_estructura(
    hojas_base: dict[str, pd.DataFrame],
    estructura: str,
    cant: int,
    tension: float,
    calibre_mt=None,
    tabla_conectores_mt=None,
) -> pd.DataFrame:

    cant = int(cant) if cant else 1
    if cant < 1:
        cant = 1

    # =========================
    # Obtener hoja
    # =========================
    df_hoja = hojas_base.get(estructura)

    if df_hoja is None or df_hoja.empty:
        return pd.DataFrame(columns=COLUMNAS_STD)

    # =========================
    # Lector
    # =========================
    df_filtrado = leer_hoja_materiales(df_hoja, tension)

    if df_filtrado is None or df_filtrado.empty:
        return pd.DataFrame(columns=COLUMNAS_STD)

    _validar_df(df_filtrado)

    # =========================
    # Limpieza mínima
    # =========================
    df_filtrado = df_filtrado.copy()

    df_filtrado["Materiales"] = df_filtrado["Materiales"].astype(str).str.strip()
    df_filtrado["Unidad"] = df_filtrado["Unidad"].astype(str).str.strip()
    df_filtrado["Cantidad"] = pd.to_numeric(df_filtrado["Cantidad"], errors="coerce").fillna(0)

    # =========================
    # ⚠️ REEMPLAZO CONECTORES (PENDIENTE)
    # =========================
    # df_filtrado["Materiales"] = reemplazar_solo_yc25a25_mt(
    #     df_filtrado["Materiales"],
    #     estructura,
    #     calibre_mt,
    #     tabla_conectores_mt
    # )

    # =========================
    # Multiplicar por cantidad
    # =========================
    df_filtrado["Cantidad"] = df_filtrado["Cantidad"] * float(cant)

    # =========================
    # Agrupar (evitar duplicados internos)
    # =========================
    df_filtrado = (
        df_filtrado
        .groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"]
        .sum()
    )

    _validar_df(df_filtrado)

    return df_filtrado[COLUMNAS_STD]


# ==========================================================
# MATERIAL POR PROYECTO (PUNTOS)
# ==========================================================
def calcular_materiales_por_punto(
    hojas_base: dict[str, pd.DataFrame],
    df_estructuras: pd.DataFrame,
    tension: float,
    calibre_mt=None,
    tabla_conectores_mt=None,
) -> pd.DataFrame:

    conteo, _ = extraer_conteo_estructuras(df_estructuras)

    resultados = []

    for estructura, cant in conteo.items():

        df_mat = calcular_materiales_estructura(
            hojas_base=hojas_base,
            estructura=estructura,
            cant=cant,
            tension=tension,
            calibre_mt=calibre_mt,
            tabla_conectores_mt=tabla_conectores_mt
        )

        if df_mat is not None and not df_mat.empty:
            resultados.append(df_mat)

    if not resultados:
        return pd.DataFrame(columns=COLUMNAS_STD)

    df_final = pd.concat(resultados, ignore_index=True)

    _validar_df(df_final)

    return df_final[COLUMNAS_STD]
