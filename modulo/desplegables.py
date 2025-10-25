# modulo/desplegables.py
# -*- coding: utf-8 -*-

import os
import pandas as pd
import streamlit as st

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
RUTA_EXCEL = os.path.join(REPO_ROOT, "data", "Estructura_datos.xlsx")


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
        codigos = subset[cod_col].dropna().astype(str).tolist()
        etiquetas = {
            str(row[cod_col]): f"{row[cod_col]} – {row[desc_col]}"
            for _, row in subset.iterrows()
            if pd.notna(row[cod_col])
        }
        opciones[clasificacion] = {"valores": codigos, "etiquetas": etiquetas}

    # Normalizamos claves para que encajen con los campos de tu UI
    mapping = {
        "Poste": "Poste",
        "Primaria": "Primario",
        "Secundaria": "Secundario",
        "Retenidas": "Retenidas",
        "Conexiones a tierra": "Conexiones a tierra",
        "Transformadores": "Transformadores",
    }
    normalizado = {}
    for k, v in opciones.items():
        normalizado[mapping.get(k, k)] = v
    return normalizado


def multiselect_con_etiquetas(label, datos, key, valores_previos_str=""):
    """
    Multiselect que recuerda lo ya guardado (si existe).
    Devuelve una cadena con los códigos separados por coma y espacio: 'A-I-5 , R-1'.
    """
    if not datos:
        return ""

    # Cargar selección previa (si hay) separando por coma
    valores_previos = []
    if valores_previos_str:
        valores_previos = [
            v.strip()
            for v in str(valores_previos_str).split(",")
            if v.strip() in datos["valores"]
        ]

    seleccionados = st.multiselect(
        label,
        options=datos["valores"],
        default=valores_previos,
        format_func=lambda x: datos["etiquetas"].get(x, x),
        key=key,
    )

    return " , ".join(seleccionados) if seleccionados else ""


def crear_desplegables(opciones):
    """
    Crea multiselects para Poste / Primario / Secundario / Retenidas /
    Conexiones a tierra / Transformadores.
    """
    seleccion = {}
    df_actual = st.session_state.get("df_puntos", pd.DataFrame())
    punto_actual = st.session_state.get("punto_en_edicion")

    # Valores previos del punto (si existe)
    valores_previos = {}
    if not df_actual.empty and punto_actual in df_actual.get("Punto", pd.Series(dtype=str)).values:
        fila = df_actual[df_actual["Punto"] == punto_actual].iloc[0].to_dict()
        valores_previos = {k: v for k, v in fila.items() if k != "Punto"}

    # Seis columnas, como antes
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        seleccion["Poste"] = multiselect_con_etiquetas(
            "Poste",
            opciones.get("Poste"),
            key="sel_poste",
            valores_previos_str=valores_previos.get("Poste", ""),
        )

    with col2:
        seleccion["Primario"] = multiselect_con_etiquetas(
            "Primario",
            opciones.get("Primario"),
            key="sel_primario",
            valores_previos_str=valores_previos.get("Primario", ""),
        )

    with col3:
        seleccion["Secundario"] = multiselect_con_etiquetas(
            "Secundario",
            opciones.get("Secundario"),
            key="sel_secundario",
            valores_previos_str=valores_previos.get("Secundario", ""),
        )

    with col4:
        seleccion["Retenidas"] = multiselect_con_etiquetas(
            "Retenidas",
            opciones.get("Retenidas"),
            key="sel_retenidas",
            valores_previos_str=valores_previos.get("Retenidas", ""),
        )

    with col5:
        seleccion["Conexiones a tierra"] = multiselect_con_etiquetas(
            "Conexiones a tierra",
            opciones.get("Conexiones a tierra"),
            key="sel_tierra",
            valores_previos_str=valores_previos.get("Conexiones a tierra", ""),
        )

    with col6:
        seleccion["Transformadores"] = multiselect_con_etiquetas(
            "Transformadores",
            opciones.get("Transformadores"),
            key="sel_transformador",
            valores_previos_str=valores_previos.get("Transformadores", ""),
        )

    return seleccion

    return valores

