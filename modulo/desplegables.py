# modulo/desplegables.py
import os
import pandas as pd
import streamlit as st

RUTA_EXCEL = os.path.join(os.path.dirname(__file__), "Estructura_datos.xlsx")

def cargar_opciones():
    """Lee la hoja 'indice' y organiza por Clasificación (código + descripción)."""
    df = pd.read_excel(RUTA_EXCEL, sheet_name="indice")
    df.columns = df.columns.str.strip()

    opciones = {}

    # estructuras (primaria, secundaria, etc.)
    for clasificacion in df["Clasificación"].unique():
        if clasificacion.startswith("Poste"):  # 👈 ignoramos postes aquí
            continue
        subset = df[df["Clasificación"] == clasificacion]
        codigos = [
            (f"{row['Código de Estructura']} – {row['Descripción']}", row["Código de Estructura"])
            for _, row in subset.iterrows()
        ]
        opciones[clasificacion] = codigos

    # postes: juntamos todas las clasificaciones que contengan "Poste"
    df_postes = df[df["Clasificación"].str.contains("Poste", case=False, na=False)]
    opciones["Poste"] = df_postes["Código de Estructura"].dropna().tolist()

    return opciones



def crear_desplegables(opciones):
    """Crea los selectbox y devuelve un diccionario con la selección (solo código)."""
    seleccion = {}
    seleccion["Punto"] = st.number_input("Selecciona Punto:", min_value=1, step=1)

    # 🔹 Poste directo desde Excel
    seleccion["Poste"] = st.selectbox(
        "Selecciona Poste:",
        opciones.get("Poste", [])
    )

    # 🔹 Estructuras normales
    seleccion["Primario"] = st.selectbox(
        "Selecciona Primario:",
        opciones.get("Primaria", []),
        format_func=lambda x: x[0] if isinstance(x, tuple) else x
    )[1] if opciones.get("Primaria") else ""

    seleccion["Secundario"] = st.selectbox(
        "Selecciona Secundario:",
        opciones.get("Secundaria", []),
        format_func=lambda x: x[0] if isinstance(x, tuple) else x
    )[1] if opciones.get("Secundaria") else ""

    seleccion["Retenida"] = st.selectbox(
        "Selecciona Retenida:",
        opciones.get("Retenida", []),
        format_func=lambda x: x[0] if isinstance(x, tuple) else x
    )[1] if opciones.get("Retenida") else ""

    seleccion["Aterrizaje"] = st.selectbox(
        "Selecciona Aterrizaje:",
        opciones.get("Aterrizaje", []),
        format_func=lambda x: x[0] if isinstance(x, tuple) else x
    )[1] if opciones.get("Aterrizaje") else ""

    seleccion["Transformador"] = st.selectbox(
        "Selecciona Transformador:",
        opciones.get("Transformador", []),
        format_func=lambda x: x[0] if isinstance(x, tuple) else x
    )[1] if opciones.get("Transformador") else ""

    return seleccion


