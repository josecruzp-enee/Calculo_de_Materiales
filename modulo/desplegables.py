# modulo/desplegables.py
# -*- coding: utf-8 -*-
import os
import pandas as pd
import streamlit as st

# Ruta al Excel
RUTA_EXCEL = os.path.join(os.path.dirname(__file__), "Estructura_datos.xlsx")

def cargar_opciones():
    """Lee la hoja 'indice' y organiza opciones por Clasificación."""
    df = pd.read_excel(RUTA_EXCEL, sheet_name="indice")
    df.columns = df.columns.str.strip()  # elimina espacios raros en encabezados

    clas_col = "Clasificación" if "Clasificación" in df.columns else "Clasificacion"
    cod_col  = "Código de Estructura" if "Código de Estructura" in df.columns else "Codigo de Estructura"
    desc_col = "Descripción" if "Descripción" in df.columns else "Descripcion"

    opciones = {}

    for clasificacion in df[clas_col].dropna().unique():
        subset = df[df[clas_col] == clasificacion]

        if str(clasificacion).lower() == "poste":
            # Para postes solo usamos código
            codigos = subset[cod_col].dropna().tolist()
        else:
            # Para las demás clasificaciones: código + descripción
            codigos = [
                (f"{row[cod_col]} – {row[desc_col]}", row[cod_col])
                for _, row in subset.iterrows()
                if pd.notna(row[cod_col])
            ]
        opciones[clasificacion] = codigos

    return opciones


def crear_desplegables(opciones):
    """Crea los selectbox para cada columna y devuelve selección solo con códigos."""
    seleccion = {}
    seleccion["Punto"] = st.number_input("Selecciona Punto:", min_value=1, step=1)

    # Poste
    seleccion["Poste"] = st.selectbox("Selecciona Poste:", opciones.get("Poste", []))

    # Primario
    seleccion["Primario"] = st.selectbox(
        "Selecciona Primario:",
        opciones.get("Primaria", []),
        format_func=lambda x: x[0] if isinstance(x, tuple) else x
    )

    # Secundario
    seleccion["Secundario"] = st.selectbox(
        "Selecciona Secundario:",
        opciones.get("Secundaria", []),
        format_func=lambda x: x[0] if isinstance(x, tuple) else x
    )

    # Retenida
    seleccion["Retenida"] = st.selectbox(
        "Selecciona Retenida:",
        opciones.get("Retenida", []),
        format_func=lambda x: x[0] if isinstance(x, tuple) else x
    )

    # Aterrizaje
    seleccion["Aterrizaje"] = st.selectbox(
        "Selecciona Aterrizaje:",
        opciones.get("Aterrizaje", []),
        format_func=lambda x: x[0] if isinstance(x, tuple) else x
    )

    # Transformador
    seleccion["Transformador"] = st.selectbox(
        "Selecciona Transformador:",
        opciones.get("Transformador", []),
        format_func=lambda x: x[0] if isinstance(x, tuple) else x
    )

    # devolvemos solo el código (no la descripción)
    for k, v in seleccion.items():
        if isinstance(v, tuple):
            seleccion[k] = v[1]

    return seleccion
