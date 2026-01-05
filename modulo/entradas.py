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
        # Normalizar nombres de columnas
        df.columns = df.columns.str.strip().str.upper()

        # Renombrar columnas conocidas
        if "CÓDIGO" in df.columns:
            df = df.rename(columns={"CÓDIGO": "Codigo"})
        if "DESCRIPCIÓN  DE  MATERIAL" in df.columns:
            df = df.rename(columns={"DESCRIPCIÓN  DE  MATERIAL": "Descripcion"})
        elif "DESCRIPCIÓN DE MATERIAL" in df.columns:
            df = df.rename(columns={"DESCRIPCIÓN DE MATERIALES": "Descripcion"})
        elif "DESCRIPCION DE MATERIAL" in df.columns:
            df = df.rename(columns={"DESCRIPCION DE MATERIAL": "Descripcion"})
        if "UNIDAD" in df.columns:
            df = df.rename(columns={"UNIDAD": "Unidad"})

        # Mantener solo columnas que interesan
        cols = [c for c in ["Codigo", "Descripcion", "Unidad"] if c in df.columns]
        return df[cols].dropna().reset_index(drop=True)

    except Exception as e:
        print(f"⚠️ Error cargando hoja 'Materiales': {e}")
        return pd.DataFrame(columns=["Descripcion", "Unidad"])

def cargar_adicionales(archivo_estructuras):
    try:
        df_adicionales = pd.read_excel(archivo_estructuras, sheet_name='materialesadicionados')
        if all(c in df_adicionales.columns for c in ['Material', 'Unidad', 'Cantidad']):
            return df_adicionales.rename(columns={'Material': 'Materiales'})
    except:
        pass
    return pd.DataFrame(columns=['Materiales', 'Unidad', 'Cantidad'])





