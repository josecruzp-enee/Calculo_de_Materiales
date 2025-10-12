import os
import pandas as pd
import streamlit as st

# Ruta al Excel
RUTA_EXCEL = os.path.join(os.path.dirname(__file__), "Estructura_datos.xlsx")


def cargar_opciones():
    """Lee la hoja 'indice' y organiza opciones por Clasificación."""
    df = pd.read_excel(RUTA_EXCEL, sheet_name="indice")
    df.columns = df.columns.str.strip()

    clas_col = "Clasificación" if "Clasificación" in df.columns else "Clasificacion"
    cod_col = "Código de Estructura" if "Código de Estructura" in df.columns else "Codigo de Estructura"
    desc_col = "Descripción" if "Descripción" in df.columns else "Descripcion"

    opciones = {}
    for clasificacion in df[clas_col].dropna().unique():
        subset = df[df[clas_col] == clasificacion]
        codigos = subset[cod_col].dropna().tolist()
        etiquetas = {
            row[cod_col]: f"{row[cod_col]} – {row[desc_col]}"
            for _, row in subset.iterrows() if pd.notna(row[cod_col])
        }
        opciones[clasificacion] = {"valores": codigos, "etiquetas": etiquetas}

    return opciones


def crear_desplegables(opciones):
    """Crea selectbox para cada tipo de estructura en una sola fila."""
    seleccion = {}

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        seleccion["Poste"] = st.selectbox(
            "Poste", ["Seleccionar estructura"] + opciones.get("Poste", {}).get("valores", []),
            index=0, key="sel_poste"
        )
    with col2:
        seleccion["Primario"] = st.selectbox(
            "Primario", ["Seleccionar estructura"] + opciones.get("Primaria", {}).get("valores", []),
            index=0, key="sel_primario"
        )
    with col3:
        seleccion["Secundario"] = st.selectbox(
            "Secundario", ["Seleccionar estructura"] + opciones.get("Secundaria", {}).get("valores", []),
            index=0, key="sel_secundario"
        )
    with col4:
        seleccion["Retenidas"] = st.selectbox(
            "Retenida", ["Seleccionar estructura"] + opciones.get("Retenidas", {}).get("valores", []),
            index=0, key="sel_retenidas"
        )
    with col5:
        seleccion["Conexiones a tierra"] = st.selectbox(
            "Aterrizaje", ["Seleccionar estructura"] + opciones.get("Conexiones a tierra", {}).get("valores", []),
            index=0, key="sel_tierra"
        )
    with col6:
        seleccion["Transformadores"] = st.selectbox(
            "Transformador", ["Seleccionar estructura"] + opciones.get("Transformadores", {}).get("valores", []),
            index=0, key="sel_transformador"
        )

    return seleccion
