# modulo/desplegables.py
import os
import pandas as pd
import streamlit as st

RUTA_EXCEL = os.path.join(os.path.dirname(__file__), "Estructura_datos.xlsx")

def cargar_opciones():
    """Lee la hoja 'indice' y organiza por Clasificación (código + descripción)."""
    df = pd.read_excel(RUTA_EXCEL, sheet_name="indice")

    # 🔹 limpiar nombres de columnas (quita espacios extras)
    df.columns = df.columns.str.strip()

    # 🔹 validar columnas
    columnas_esperadas = ["Clasificación", "Código de Estructura", "Descripción"]
    for col in columnas_esperadas:
        if col not in df.columns:
            st.error(f"⚠️ No se encontró la columna '{col}'. Columnas disponibles: {list(df.columns)}")
            st.stop()

    opciones = {}
    for clasificacion in df["Clasificación"].unique():
        subset = df[df["Clasificación"] == clasificacion]
        codigos = [
            (f"{row['Código de Estructura']} – {row['Descripción']}", row["Código de Estructura"])
            for _, row in subset.iterrows()
        ]
        opciones[clasificacion] = codigos
    return opciones


def crear_desplegables(opciones):
    """Crea los selectbox y devuelve un diccionario con la selección (solo código)."""
    seleccion = {}
    seleccion["Punto"] = st.number_input("Selecciona Punto:", min_value=1, step=1)

    seleccion["Poste"] = st.selectbox(
        "Selecciona Poste:",
        opciones.get("Poste", [])
    )
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
