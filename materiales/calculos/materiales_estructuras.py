# -*- coding: utf-8 -*-

import pandas as pd
from collections import Counter

from materiales.auxiliares.materiales_aux import limpiar_codigo, expandir_lista_codigos
from entradas.excel_legacy import extraer_estructuras_proyectadas

# reemplazo de conectores
from core.conectores_mt import reemplazar_solo_yc25a25_mt

# nuevo lector unificado
from materiales.auxiliares.lector_materiales import leer_hoja_materiales


# ==========================================================
# Conteo de estructuras
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
# Materiales por ESTRUCTURA
# ==========================================================
def calcular_materiales_estructura(
    archivo_materiales,
    estructura,
    cant,
    tension,
    calibre_mt,
    tabla_conectores_mt
):
    """
    Calcula materiales por estructura individual.
    """

    try:
        cant = int(cant) if cant else 1
        if cant < 1:
            cant = 1

        # =========================
        # LECTOR UNIFICADO (CLAVE)
        # =========================
        df_filtrado = leer_hoja_materiales(archivo_materiales, estructura, tension)

        if df_filtrado is None or df_filtrado.empty:
            return pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])

        # =========================
        # LIMPIEZA
        # =========================
        df_filtrado["Materiales"] = df_filtrado["Materiales"].astype(str).str.strip()
        df_filtrado["Unidad"] = df_filtrado["Unidad"].astype(str).str.strip()
        df_filtrado["Cantidad"] = pd.to_numeric(df_filtrado["Cantidad"], errors="coerce").fillna(0)

        # =========================
        # REEMPLAZO CONECTORES MT
        # =========================
        df_filtrado["Materiales"] = reemplazar_solo_yc25a25_mt(
            df_filtrado["Materiales"].tolist(),
            estructura,
            calibre_mt,
            tabla_conectores_mt
        )

        # =========================
        # MULTIPLICAR POR CANTIDAD
        # =========================
        df_filtrado["Cantidad"] = df_filtrado["Cantidad"] * float(cant)

        # =========================
        # AGRUPAR
        # =========================
        df_filtrado = (
            df_filtrado
            .groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"]
            .sum()
        )

        return df_filtrado[["Materiales", "Unidad", "Cantidad"]]

    except Exception as e:
        print(f"⚠️ Error en estructura {estructura}: {e}")
        return pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])
