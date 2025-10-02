# modulo/desplegables.py
import streamlit as st
import pandas as pd

RUTA_EXCEL = os.path.join(os.path.dirname(__file__), "Estructura_datos.xlsx")

def cargar_opciones():
    """Lee la hoja 'indice' y organiza por Clasificación (código + descripción)."""
    df = pd.read_excel(RUTA_EXCEL, sheet_name="indice")

    opciones = {}
    for clasificacion in df["Clasificación"].unique():
        subset = df[df["Clasificación"] == clasificacion]
        # lista de tuplas: (etiqueta para mostrar, código real)
        codigos = [(f"{row['Código de Estructura']} – {row['Descripción']}", row["Código de Estructura"])
                   for _, row in subset.iterrows()]
        opciones[clasificacion] = codigos
    return opciones


def crear_desplegables(opciones):
    """Crea los selectbox y devuelve un diccionario con la selección (solo código)."""
    seleccion = {}
    seleccion["Punto"] = st.number_input("Selecciona Punto:", min_value=1, step=1)

    # usamos format_func para mostrar etiqueta pero guardar solo el código
    seleccion["Poste"] = st.selectbox(
        "Selecciona Poste:",
        opciones.get("Poste", []),
        format_func=lambda x: x[0] if isinstance(x, tuple) else x
    )[1] if opciones.get("Poste") else ""

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

