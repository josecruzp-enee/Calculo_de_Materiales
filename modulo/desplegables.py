# modulo/desplegables.py
import os
import pandas as pd
import streamlit as st

# Ruta al Excel
RUTA_EXCEL = os.path.join(os.path.dirname(__file__), "Estructura_datos.xlsx")

def cargar_opciones():
    """Lee la hoja 'indice' y organiza opciones por Clasificación."""
    opciones = {}
    try:
        df = pd.read_excel(RUTA_EXCEL, sheet_name="indice")
    except Exception as e:
        st.warning(f"No se pudo leer 'Estructura_datos.xlsx' (indice): {e}")
        return opciones  # ← devolvemos vacío para no romper el import

    df.columns = df.columns.str.strip()

    clas_col = "Clasificación" if "Clasificación" in df.columns else "Clasificacion"
    cod_col  = "Código de Estructura" if "Código de Estructura" in df.columns else "Codigo de Estructura"
    desc_col = "Descripción" if "Descripción" in df.columns else "Descripcion"

    for clasificacion in df.get(clas_col, pd.Series()).dropna().unique():
        subset = df[df[clas_col] == clasificacion]
        if cod_col not in subset.columns or desc_col not in subset.columns:
            continue

        codigos = subset[cod_col].dropna().astype(str).tolist()
        etiquetas = {
            str(row[cod_col]): f"{row[cod_col]} – {row.get(desc_col, '')}"
            for _, row in subset.iterrows()
            if pd.notna(row.get(cod_col))
        }
        opciones[str(clasificacion)] = {"valores": codigos, "etiquetas": etiquetas}

    return opciones

def crear_desplegables(opciones):
    """
    Crea selectbox para cada tipo de estructura con 'Seleccionar estructura' como default.
    Devuelve un dict con los valores seleccionados (o 'Seleccionar estructura').
    """
    seleccion = {}

    def selectbox_con_etiquetas(label, datos, key):
        if not datos or "valores" not in datos or "etiquetas" not in datos:
            # si no hay datos, mostramos sólo el placeholder
            return st.selectbox(label, options=["Seleccionar estructura"], key=key)

        opciones_lista = ["Seleccionar estructura"] + list(datos["valores"])
        return st.selectbox(
            label,
            options=opciones_lista,
            format_func=lambda x: datos["etiquetas"].get(x, x) if x in datos["valores"] else x,
            key=key
        )

    seleccion["Poste"] = selectbox_con_etiquetas("Selecciona Poste:", opciones.get("Poste"), key="sel_poste")
    seleccion["Primario"] = selectbox_con_etiquetas("Selecciona Primario:", opciones.get("Primaria"), key="sel_primario")
    seleccion["Secundario"] = selectbox_con_etiquetas("Selecciona Secundario:", opciones.get("Secundaria"), key="sel_secundario")
    seleccion["Retenidas"] = selectbox_con_etiquetas("Selecciona Retenida:", opciones.get("Retenidas") or opciones.get("Retenida"), key="sel_retenidas")
    seleccion["Conexiones a tierra"] = selectbox_con_etiquetas("Selecciona Aterrizaje:", opciones.get("Conexiones a tierra") or opciones.get("Aterrizaje"), key="sel_tierra")
    seleccion["Transformadores"] = selectbox_con_etiquetas("Selecciona Transformador:", opciones.get("Transformadores") or opciones.get("Transformador"), key="sel_transformador")

    return seleccion
