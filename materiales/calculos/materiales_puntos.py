# -*- coding: utf-8 -*-

from __future__ import annotations
import pandas as pd
from collections import Counter

from materiales.auxiliares.materiales_aux import limpiar_codigo, expandir_lista_codigos
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

    # 🔥 Validaciones adicionales reales
    if df["Materiales"].isna().any():
        raise ValueError("Materiales contiene valores nulos")

    if df["Unidad"].isna().any():
        raise ValueError("Unidad contiene valores nulos")

    if (pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0) < 0).any():
        raise ValueError("Cantidad contiene valores negativos")


# ==========================================================
# LIMPIEZA SEGURA
# ==========================================================
def _limpiar_str(v) -> str:
    if pd.isna(v):
        return ""
    return str(v).strip()


# ==========================================================
# NORMALIZACIÓN DE ESTRUCTURAS (SIN DUPLICAR LÓGICA)
# ==========================================================
def _normalizar_estructura(e: str) -> str | None:

    e = _limpiar_str(e)

    if not e or e.lower() in {"nan", "none", "0"}:
        return None

    for parte in expandir_lista_codigos(e):

        parte = _limpiar_str(parte)

        if not parte:
            continue

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

        punto = _limpiar_str(row.get("Punto")) or "Punto"
        estructuras_raw = _limpiar_str(row.get("Estructuras"))

        if not estructuras_raw:
            estructuras_por_punto[punto] = []
            continue

        lista = estructuras_raw.split(";")
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
# MATERIAL POR ESTRUCTURA (CORREGIDO)
# ==========================================================
def calcular_materiales_estructura(
    hojas_base,
    estructura,
    cant,
    tension,
    calibre_mt=None,
    tabla_conectores_mt=None,
):

    estructura = _limpiar_str(estructura).upper()

    if not estructura:
        raise ValueError("Estructura vacía")

    if cant is None or float(cant) <= 0:
        raise ValueError(f"Cantidad inválida para {estructura}: {cant}")

    cant = int(cant)

    # 🔥 VALIDACIÓN REAL (ANTES SILENCIOSA)
    df_hoja = hojas_base.get(estructura)

    if df_hoja is None:
        raise ValueError(f"Estructura no encontrada en base de datos: {estructura}")

    if df_hoja.empty:
        raise ValueError(f"Hoja vacía para estructura: {estructura}")

    df_filtrado = leer_hoja_materiales(df_hoja, tension)

    if df_filtrado is None or df_filtrado.empty:
        raise ValueError(f"No hay materiales para estructura {estructura} en tensión {tension}")

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
