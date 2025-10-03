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
            # Para postes solo usamos el código
            codigos = subset[cod_col].dropna().tolist()
            etiquetas = {c: c for c in codigos}
        else:
            # Para las demás: usamos el código como valor y mostramos código + descripción
            codigos = subset[cod_col].dropna().tolist()
            etiquetas = {
                row[cod_col]: f"{row[cod_col]} – {row[desc_col]}"
                for _, row in subset.iterrows()
                if pd.notna(row[cod_col])
            }
        opciones[clasificacion] = {"valores": codigos, "etiquetas": etiquetas}

    return opciones


def crear_desplegables(opciones):
    """Crea los selectbox para cada columna y devuelve selección solo con códigos."""
    seleccion = {}

    def selectbox_con_etiquetas(label, datos):
        if not datos:
            return None
        return st.selectbox(
            label,
            options=datos["valores"],
            format_func=lambda x: datos["etiquetas"].get(x, x)
        )

    # Poste
    seleccion["Poste"] = selectbox_con_etiquetas("Selecciona Poste:", opciones.get("Poste"))
    # Primario
    seleccion["Primario"] = selectbox_con_etiquetas("Selecciona Primario:", opciones.get("Primaria"))
    # Secundario
    seleccion["Secundario"] = selectbox_con_etiquetas("Selecciona Secundario:", opciones.get("Secundaria"))
    # Retenida
    seleccion["Retenidas"] = selectbox_con_etiquetas("Selecciona Retenida:", opciones.get("Retenida"))
    # Aterrizaje
    seleccion["Conexiones a tierra"] = selectbox_con_etiquetas("Selecciona Aterrizaje:", opciones.get("Aterrizaje"))
    # Transformador
    seleccion["Transformadores"] = selectbox_con_etiquetas("Selecciona Transformador:", opciones.get("Transformador"))

    return seleccion

