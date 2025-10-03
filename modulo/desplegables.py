# modulo/desplegables.py
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
    cod_col  = "Código de Estructura" if "Código de Estructura" in df.columns else "Codigo de Estructura"
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
    """Crea selectbox para cada tipo de estructura con opción inicial 'Seleccionar estructura'."""
    seleccion = {}

    def selectbox_con_etiquetas(label, datos):
        if not datos:
            return None
        lista_opciones = ["Seleccionar estructura"] + datos["valores"]
        etiquetas = {"Seleccionar estructura": "Seleccionar estructura", **datos["etiquetas"]}

        elegido = st.selectbox(
            label,
            options=lista_opciones,
            format_func=lambda x: etiquetas.get(x, x),
            index=0  # 👈 siempre arranca en "Seleccionar estructura"
        )
        return None if elegido == "Seleccionar estructura" else elegido

    # Agrupación de categorías
    seleccion["Poste"] = selectbox_con_etiquetas("Selecciona Poste:", opciones.get("Poste"))
    seleccion["Primario"] = selectbox_con_etiquetas("Selecciona Primario:", opciones.get("Primaria"))
    seleccion["Secundario"] = selectbox_con_etiquetas("Selecciona Secundario:", opciones.get("Secundaria"))
    seleccion["Retenidas"] = selectbox_con_etiquetas("Selecciona Retenida:", opciones.get("Retenidas"))
    seleccion["Conexiones a tierra"] = selectbox_con_etiquetas("Selecciona Aterrizaje:", opciones.get("Conexiones a tierra"))
    seleccion["Transformadores"] = selectbox_con_etiquetas("Selecciona Transformador:", opciones.get("Transformadores"))

    return seleccion
