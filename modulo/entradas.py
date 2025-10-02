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
    estructuras_proyectadas, estructuras_por_punto = [], {}
    for i, fila in df_estructuras.iterrows():
        punto = fila.get("Punto #", f"Punto {i+1}")
        estructuras_en_fila = []
        for col in df_estructuras.columns:
            celda = fila[col]
            if pd.notna(celda):
                celda_str = str(celda).replace("\n", " ").replace("\r", " ").strip()
                patrones = re.findall(r"(?:(\d+)\s*)?([A-Z0-9\-\.]+)(?:\s*\(\s*P\s*\))?", celda_str, flags=re.IGNORECASE)
                for cantidad_str, nombre in patrones:
                    cantidad = int(cantidad_str) if cantidad_str else 1
                    estructuras_en_fila.extend([nombre]*cantidad)
                    estructuras_proyectadas.extend([nombre]*cantidad)
        estructuras_por_punto[punto] = estructuras_en_fila
    return estructuras_proyectadas, estructuras_por_punto

def cargar_materiales(archivo_materiales, hoja, header=None):
    return pd.read_excel(archivo_materiales, sheet_name=hoja, header=header)

def cargar_indice(archivo_materiales):
    df_indice = pd.read_excel(archivo_materiales, sheet_name='indice', usecols=[3, 4])
    df_indice.columns = ['NombreEstructura', 'Descripcion']
    return df_indice

def cargar_adicionales(archivo_estructuras):
    try:
        df_adicionales = pd.read_excel(archivo_estructuras, sheet_name='materialesadicionados')
        if all(c in df_adicionales.columns for c in ['Material', 'Unidad', 'Cantidad']):
            return df_adicionales.rename(columns={'Material': 'Materiales'})
    except:
        pass
    return pd.DataFrame(columns=['Materiales', 'Unidad', 'Cantidad'])

