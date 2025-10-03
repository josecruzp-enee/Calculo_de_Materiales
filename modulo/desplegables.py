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
    """
    Crea los selectbox para estructuras agrupadas:
    - Primarias: Tramo MT y Estructuras Especiales (DT, H, TM, Especial)
    - Secundarias: Secundarias y Neutro
    """
    seleccion = {}

    def selectbox_etiquetas(label, datos):
        if not datos:
            return None
        # Armamos lista con "Seleccionar estructura" al inicio
        lista = datos.get("valores", [])
        etiquetas = datos.get("etiquetas", {})

        lista_opciones = ["Seleccionar estructura"] + lista
        return st.selectbox(
            label,
            options=lista_opciones,
            format_func=lambda x: etiquetas.get(x, x) if x != "Seleccionar estructura" else x,
            index=0
        )

    # -----------------------
    # ⚡ PRIMARIAS
    # -----------------------
    st.markdown("#### ⚡ Estructuras Primarias")

    seleccion["Primario"] = selectbox_etiquetas("Selecciona Tramo MT:", opciones.get("Primaria"))
    seleccion["Especiales"] = selectbox_etiquetas("Selecciona Estructura Especial (DT, H, TM, Especial):", opciones.get("Especiales"))

    # -----------------------
    # 🔌 SECUNDARIAS
    # -----------------------
    st.markdown("#### 🔌 Estructuras Secundarias")

    seleccion["Secundario"] = selectbox_etiquetas("Selecciona Secundaria:", opciones.get("Secundaria"))
    seleccion["Neutro"] = selectbox_etiquetas("Selecciona Neutro:", opciones.get("Neutro"))

    # -----------------------
    # Otros (retenida, tierra, transf.)
    # -----------------------
    st.markdown("#### 📦 Otros Elementos")

    seleccion["Retenidas"] = selectbox_etiquetas("Selecciona Retenida:", opciones.get("Retenida"))
    seleccion["Conexiones a tierra"] = selectbox_etiquetas("Selecciona Aterrizaje:", opciones.get("Aterrizaje"))
    seleccion["Transformadores"] = selectbox_etiquetas("Selecciona Transformador:", opciones.get("Transformador"))

    return seleccion




    # Poste
    seleccion["Poste"] = selectbox_con_etiquetas("Selecciona Poste:", opciones.get("Poste"))
    # Primario
    seleccion["Primario"] = selectbox_con_etiquetas("Selecciona Primario:", opciones.get("Primaria"))
    # Secundario
    seleccion["Secundario"] = selectbox_con_etiquetas("Selecciona Secundario:", opciones.get("Secundaria"))
    # Retenida (clave = "Retenida", aunque el label diga "Selecciona Retenida")
    seleccion["Retenidas"] = selectbox_con_etiquetas("Selecciona Retenida:", opciones.get("Retenida") or opciones.get("Retenidas"))
    # Aterrizaje (clave = "Aterrizaje")
    seleccion["Conexiones a tierra"] = selectbox_con_etiquetas("Selecciona Aterrizaje:", opciones.get("Aterrizaje") or opciones.get("Conexiones a tierra"))
    # Transformador (clave = "Transformador")
    seleccion["Transformadores"] = selectbox_con_etiquetas("Selecciona Transformador:", opciones.get("Transformador") or opciones.get("Transformadores"))

    return seleccion




