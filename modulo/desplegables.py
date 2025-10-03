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
    """Crea selectbox para cada tipo de estructura."""
    seleccion = {}

    def selectbox_con_etiquetas(label, datos, key):
        if not datos:
            return None
        return st.selectbox(
            label,
            options=["Seleccionar estructura"] + datos["valores"],
            index=0,  # siempre arranca en "Seleccionar estructura"
            format_func=lambda x: datos["etiquetas"].get(x, x) if x in datos["valores"] else x,
            key=key
        )

    seleccion["Poste"] = selectbox_con_etiquetas("Selecciona Poste:", opciones.get("Poste"), "sel_poste")
    seleccion["Primario"] = selectbox_con_etiquetas("Selecciona Primario:", opciones.get("Primaria"), "sel_primario")
    seleccion["Secundario"] = selectbox_con_etiquetas("Selecciona Secundario:", opciones.get("Secundaria"), "sel_secundario")
    seleccion["Retenidas"] = selectbox_con_etiquetas("Selecciona Retenida:", opciones.get("Retenidas"), "sel_retenidas")
    seleccion["Conexiones a tierra"] = selectbox_con_etiquetas("Selecciona Aterrizaje:", opciones.get("Conexiones a tierra"), "sel_tierra")
    seleccion["Transformadores"] = selectbox_con_etiquetas("Selecciona Transformador:", opciones.get("Transformadores"), "sel_transformador")

    return seleccion
