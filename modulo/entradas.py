# -*- coding: utf-8 -*-
"""
entradas.py
Módulo para cargar insumos desde Excel u otras fuentes.
"""

import pandas as pd
import re

def cargar_datos_proyecto(archivo_estructuras):
    df_proyecto = pd.read_excel(archivo_estructuras, sheet_name='datos_proyecto', usecols=[0, 1], nrows=10)
    return {str(r[0]).strip().lower().replace(":", ""): str(r[1]).strip() for r in df_proyecto.values}

def cargar_estructuras_proyectadas(archivo_estructuras):
    return pd.read_excel(archivo_estructuras, sheet_name='estructuras')

def extraer_estructuras_proyectadas(df_estructuras):
    """
    Extrae las estructuras proyectadas desde el DataFrame base.
    Cada punto se procesa una sola vez y se evita duplicar combinaciones.
    """
    estructuras_proyectadas = []
    estructuras_por_punto = {}

    for i, fila in df_estructuras.iterrows():
        punto = fila.get("Punto #", fila.get("Punto", f"Punto {i+1}"))

        estructuras_en_punto = []
        for col in df_estructuras.columns:
            valor = fila[col]
            if pd.notna(valor):
                texto = str(valor).strip()
                if texto and texto.upper() not in ["SELECCIONAR", "ESTRUCTURA", "N/A", "NONE"]:
                    # separar estructuras en caso de múltiples valores por celda
                    partes = [p.strip() for p in texto.replace("\n", " ").split(" ") if p.strip()]
                    for parte in partes:
                        # mantener solo códigos válidos
                        if any(c.isalpha() for c in parte):
                            estructuras_en_punto.append(parte)

        # ⚙️ eliminar duplicados dentro del punto
        estructuras_en_punto = list(dict.fromkeys(estructuras_en_punto))
        estructuras_proyectadas.extend(estructuras_en_punto)
        estructuras_por_punto[punto] = estructuras_en_punto

    # ⚙️ eliminar duplicados globales
    estructuras_proyectadas = list(dict.fromkeys(estructuras_proyectadas))

    return estructuras_proyectadas, estructuras_por_punto


def cargar_materiales(archivo_materiales, hoja, header=None):
    return pd.read_excel(archivo_materiales, sheet_name=hoja, header=header)

def cargar_indice(archivo_materiales):
    """
    Carga la hoja 'indice' del archivo de materiales.
    Normaliza las columnas y devuelve un DataFrame con:
    - codigodeestructura
    - descripcion
    """
    try:
        df_indice = pd.read_excel(archivo_materiales, sheet_name='indice')
        df_indice.columns = df_indice.columns.str.strip().str.lower()

        # Detectar y renombrar columnas clave
        posibles_codigos = [
            "código de estructura", "codigo de estructura",
            "nombreestructura", "nombre estructura", "estructura"
        ]
        for col in posibles_codigos:
            if col in df_indice.columns:
                df_indice.rename(columns={col: "codigodeestructura"}, inplace=True)
                break

        posibles_desc = ["descripcion", "descripción"]
        for col in posibles_desc:
            if col in df_indice.columns:
                df_indice.rename(columns={col: "descripcion"}, inplace=True)
                break

        # Mantener solo las columnas relevantes
        columnas_validas = ["codigodeestructura", "descripcion"]
        df_indice = df_indice[[c for c in columnas_validas if c in df_indice.columns]]

        return df_indice

    except Exception as e:
        print(f"⚠️ Error al cargar índice: {e}")
        return pd.DataFrame(columns=["codigodeestructura", "descripcion"])


import pandas as pd
import re

def cargar_catalogo_materiales(archivo_materiales):
    """
    Carga la hoja 'Materiales' desde el archivo base.
    Devuelve un DataFrame con:
    - Codigo (opcional)
    - Descripcion
    - Unidad
    """
    try:
        df = pd.read_excel(archivo_materiales, sheet_name="Materiales")

        # Normalizar encabezados: strip + upper
        df.columns = df.columns.astype(str).str.strip().str.upper()

        # Helper para colapsar espacios SOLO en nombres de columnas (no toca datos)
        def _col_norm(s: str) -> str:
            return re.sub(r"\s+", " ", str(s).strip().upper())

        # Mapa de columnas por nombre "normalizado"
        col_map = {_col_norm(c): c for c in df.columns}

        # --- Código ---
        if "CÓDIGO" in df.columns:
            df = df.rename(columns={"CÓDIGO": "Codigo"})
        elif "CODIGO" in df.columns:
            df = df.rename(columns={"CODIGO": "Codigo"})

        # --- Descripción (soporta singular/plural, con/sin tilde, con espacios raros) ---
        posibles_desc = [
            "DESCRIPCIÓN DE MATERIALES",
            "DESCRIPCION DE MATERIALES",
            "DESCRIPCIÓN DE MATERIAL",
            "DESCRIPCION DE MATERIAL",
            "DESCRIPCIÓN  DE  MATERIAL",
            "DESCRIPCION  DE  MATERIAL",
            "DESCRIPCIÓN  DE  MATERIALES",
            "DESCRIPCION  DE  MATERIALES",
        ]

        for key in posibles_desc:
            k = _col_norm(key)
            if k in col_map:
                df = df.rename(columns={col_map[k]: "Descripcion"})
                break

        # --- Unidad ---
        if "UNIDAD" in df.columns:
            df = df.rename(columns={"UNIDAD": "Unidad"})
        elif "UND" in df.columns:
            df = df.rename(columns={"UND": "Unidad"})

        # Asegurar columnas aunque no existan
        if "Descripcion" not in df.columns:
            df["Descripcion"] = ""
        if "Unidad" not in df.columns:
            df["Unidad"] = ""
        if "Codigo" not in df.columns:
            df["Codigo"] = ""

        # Mantener solo columnas que interesan
        df = df[["Codigo", "Descripcion", "Unidad"]].copy()

        # Limpieza ligera (sin “normalizar” textos)
        df["Descripcion"] = df["Descripcion"].fillna("").astype(str).str.strip()
        df["Unidad"] = df["Unidad"].fillna("").astype(str).str.strip()
        df["Codigo"] = df["Codigo"].fillna("").astype(str).str.strip()

        # ❗ No borres por Unidad/Codigo vacíos: solo requiere Descripcion
        df = df[df["Descripcion"] != ""].reset_index(drop=True)

        return df

    except Exception as e:
        print(f"⚠️ Error cargando hoja 'Materiales': {e}")
        return pd.DataFrame(columns=["Codigo", "Descripcion", "Unidad"])

def cargar_adicionales(archivo_estructuras):
    try:
        df_adicionales = pd.read_excel(archivo_estructuras, sheet_name='materialesadicionados')
        if all(c in df_adicionales.columns for c in ['Material', 'Unidad', 'Cantidad']):
            return df_adicionales.rename(columns={'Material': 'Materiales'})
    except:
        pass
    return pd.DataFrame(columns=['Materiales', 'Unidad', 'Cantidad'])






