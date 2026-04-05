# -*- coding: utf-8 -*-
"""
leer_excel.py

Lectura de datos desde Excel (INPUT LIMPIO, SIN LÓGICA DE NEGOCIO).
"""

import pandas as pd
import re


# =========================================================
# HELPERS
# =========================================================
def _limpiar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _limpiar_texto_basico(s):
    if pd.isna(s):
        return ""

    s = str(s).strip()

    # eliminar saltos de línea raros
    s = s.replace("\n", " ").replace("\r", " ")

    # normalizar espacios
    s = re.sub(r"\s+", " ", s)

    return s


# =========================================================
# PROYECTO
# =========================================================
def leer_datos_proyecto(archivo):

    df = pd.read_excel(
        archivo,
        sheet_name='datos_proyecto',
        usecols=[0, 1],
        nrows=20
    )

    df = _limpiar_columnas(df)

    salida = {}

    for k, v in df.values:
        key = _limpiar_texto_basico(k).lower().replace(":", "")
        val = _limpiar_texto_basico(v)

        if key:
            salida[key] = val

    return salida


# =========================================================
# ESTRUCTURAS (CRÍTICO)
# =========================================================
def leer_estructuras(archivo) -> pd.DataFrame:
    """
    Lee estructuras SIN modificar contenido.

    NO:
        - split
        - interpretar códigos
        - normalizar estructuras

    SOLO:
        - limpiar columnas
        - limpiar texto superficial
    """

    df = pd.read_excel(archivo, sheet_name='estructuras')

    df = _limpiar_columnas(df)

    # limpieza ligera (NO lógica de negocio)
    for col in df.columns:
        df[col] = df[col].apply(_limpiar_texto_basico)

    return df


# =========================================================
# MATERIALES
# =========================================================
def leer_materiales(archivo, hoja, header=None):

    df = pd.read_excel(archivo, sheet_name=hoja, header=header)
    df = _limpiar_columnas(df)

    return df


# =========================================================
# INDICE DE ESTRUCTURAS
# =========================================================
def leer_indice_materiales(archivo):

    try:
        df = pd.read_excel(archivo, sheet_name='indice')

        df = _limpiar_columnas(df)
        df.columns = df.columns.str.lower()

        posibles_codigos = [
            "código de estructura", "codigo de estructura",
            "nombreestructura", "nombre estructura", "estructura"
        ]

        for col in posibles_codigos:
            if col in df.columns:
                df.rename(columns={col: "codigodeestructura"}, inplace=True)
                break

        posibles_desc = ["descripcion", "descripción"]

        for col in posibles_desc:
            if col in df.columns:
                df.rename(columns={col: "descripcion"}, inplace=True)
                break

        columnas_validas = ["codigodeestructura", "descripcion"]

        return df[[c for c in columnas_validas if c in df.columns]]

    except Exception:
        return pd.DataFrame(columns=["codigodeestructura", "descripcion"])


# =========================================================
# CATÁLOGO
# =========================================================
def leer_catalogo_materiales(archivo):

    try:
        df = pd.read_excel(archivo, sheet_name="Materiales")

        df = _limpiar_columnas(df)
        df.columns = df.columns.str.upper()

        def _col_norm(s: str) -> str:
            return re.sub(r"\s+", " ", str(s).strip().upper())

        col_map = {_col_norm(c): c for c in df.columns}

        # Código
        if "CÓDIGO" in df.columns:
            df.rename(columns={"CÓDIGO": "Codigo"}, inplace=True)
        elif "CODIGO" in df.columns:
            df.rename(columns={"CODIGO": "Codigo"}, inplace=True)

        # Descripción
        posibles_desc = [
            "DESCRIPCIÓN DE MATERIALES",
            "DESCRIPCION DE MATERIALES",
            "DESCRIPCIÓN DE MATERIAL",
            "DESCRIPCION DE MATERIAL",
        ]

        for key in posibles_desc:
            k = _col_norm(key)
            if k in col_map:
                df.rename(columns={col_map[k]: "Descripcion"}, inplace=True)
                break

        # Unidad
        if "UNIDAD" in df.columns:
            df.rename(columns={"UNIDAD": "Unidad"}, inplace=True)
        elif "UND" in df.columns:
            df.rename(columns={"UND": "Unidad"}, inplace=True)

        df["Descripcion"] = df.get("Descripcion", "")
        df["Unidad"] = df.get("Unidad", "")
        df["Codigo"] = df.get("Codigo", "")

        df = df[["Codigo", "Descripcion", "Unidad"]].copy()

        df["Descripcion"] = df["Descripcion"].fillna("").astype(str).str.strip()
        df["Unidad"] = df["Unidad"].fillna("").astype(str).str.strip()
        df["Codigo"] = df["Codigo"].fillna("").astype(str).str.strip()

        df = df[df["Descripcion"] != ""].reset_index(drop=True)

        return df

    except Exception:
        return pd.DataFrame(columns=["Codigo", "Descripcion", "Unidad"])


# =========================================================
# ADICIONALES
# =========================================================
def leer_adicionales(archivo):

    try:
        df = pd.read_excel(archivo, sheet_name='materialesadicionados')

        df = _limpiar_columnas(df)

        if all(c in df.columns for c in ['Material', 'Unidad', 'Cantidad']):
            return df.rename(columns={'Material': 'Materiales'})

    except Exception:
        pass

    return pd.DataFrame(columns=['Materiales', 'Unidad', 'Cantidad'])
