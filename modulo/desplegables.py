# -*- coding: utf-8 -*-
"""
Created on Thu Oct  2 10:15:49 2025

@author: José Nikol Cruz
"""

# modulo/desplegables.py
import streamlit as st
import pandas as pd

RUTA_EXCEL = "Estructura_datos.xlsx"

def cargar_opciones():
    """Lee la hoja 'indice' y agrupa códigos de estructuras por Clasificación."""
    df = pd.read_excel(RUTA_EXCEL, sheet_name="indice")

    opciones = {}
    for clasificacion in df["Clasificación"].unique():
        codigos = df[df["Clasificación"] == clasificacion]["Código de Estructura"].dropna().tolist()
        opciones[clasificacion] = codigos
    return opciones


def crear_desplegables(opciones):
    """Crea los selectbox y devuelve un diccionario con la selección."""
    seleccion = {}

    seleccion["Punto"] = st.number_input("Selecciona Punto:", min_value=1, step=1)
    seleccion["Poste"] = st.selectbox("Selecciona Poste:", opciones.get("Poste", []))
    seleccion["Primario"] = st.selectbox("Selecciona Primario:", opciones.get("Primaria", []))
    seleccion["Secundario"] = st.selectbox("Selecciona Secundario:", opciones.get("Secundaria", []))
    seleccion["Retenida"] = st.selectbox("Selecciona Retenida:", opciones.get("Retenida", []))
    seleccion["Aterrizaje"] = st.selectbox("Selecciona Aterrizaje:", opciones.get("Aterrizaje", []))
    seleccion["Transformador"] = st.selectbox("Selecciona Transformador:", opciones.get("Transformador", []))

    return seleccion
