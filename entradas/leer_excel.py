# -*- coding: utf-8 -*-
"""
leer_excel.py
Lectura de datos desde Excel (SIN lógica de negocio pesada).
"""

import pandas as pd
import re


# =========================================================
# PROYECTO
# =========================================================

def leer_datos_proyecto(archivo):
    df = pd.read_excel(archivo, sheet_name='datos_proyecto', usecols=[0, 1], nrows=10)

    return {
        str(r[0]).strip().lower().replace(":", ""): str(r[1]).strip()
        for r in df.values
    }


# =========================================================
# ESTRUCTURAS
# =========================================================

def leer_estructuras(archivo):
    return pd.read_excel(archivo, sheet_name='estructuras')


def extraer_estructuras(df):
    """
    Extrae estructuras por punto (SIN normalización avanzada).
    """
    estructuras_proyectadas = []
    estructuras_por_punto = {}

    for i, fila in df.iterrows():
        punto = fila.get("Punto #", fila.get("Punto", f"Punto {i+1}"))

        estructuras_en_punto = []

        for col in df.columns:
            valor = fila[col]

            if pd.notna(valor):
                texto = str(valor).strip()

                if texto and texto.upper() not in ["SELECCIONAR", "ESTRUCTURA", "N/A", "NONE"]:

                    partes = [
                        p.strip()
                        for p in texto.replace("\n", " ").split(" ")
                        if p.strip()
                    ]

                    for parte in partes:
                        if any(c.isalpha() for c in parte):
                            estructuras_en_punto.append(parte)

        estructuras_en_punto = list(dict.fromkeys(estructuras_en_punto))

        estructuras_proyectadas.extend(estructuras_en_punto)
        estructuras_por_punto[punto] = estructuras_en_punto

    estructuras_proyectadas = list(dict.fromkeys(estructuras_proyectadas))

    return estructuras_proyectadas, estructuras_por_punto


# =========================================================
# MATERIALES
# =========================================================

def leer_materiales(archivo, hoja, header=None):
    return pd.read_excel(archivo, sheet_name=hoja, header=header)


def leer_indice_materiales(archivo):
    try:
        df = pd.read_excel(archivo, sheet_name='indice')
        df.columns = df.columns.str.strip().str.lower()

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

        df.columns = df.columns.astype(str).str.strip().str.upper()

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

        # Asegurar columnas
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

        if all(c in df.columns for c in ['Material', 'Unidad', 'Cantidad']):
            return df.rename(columns={'Material': 'Materiales'})

    except Exception:
        pass

    return pd.DataFrame(columns=['Materiales', 'Unidad', 'Cantidad'])
