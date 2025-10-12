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
    """Crea los selectbox/multiselect para cada tipo de estructura en una sola fila."""
    seleccion = {}
    df_actual = st.session_state.get("df_puntos", pd.DataFrame())
    punto_actual = st.session_state.get("punto_en_edicion")

    # Buscar valores previos si el punto ya existe
    valores_previos = {}
    if not df_actual.empty and punto_actual in df_actual["Punto"].values:
        fila = df_actual[df_actual["Punto"] == punto_actual].iloc[0].to_dict()
        valores_previos = {k: v for k, v in fila.items() if k != "Punto"}

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    # --- Poste ---
    with col1:
        seleccion["Poste"] = st.selectbox(
            "Poste",
            ["Seleccionar estructura"] + opciones.get("Poste", {}).get("valores", []),
            index=(["Seleccionar estructura"] + opciones.get("Poste", {}).get("valores", [])).index(
                valores_previos.get("Poste", "Seleccionar estructura")
            ) if valores_previos.get("Poste") in opciones.get("Poste", {}).get("valores", []) else 0,
            key="sel_poste"
        )

    # --- Primario (ahora multiselección) ---
    with col2:
        valores_prev_primario = []
        if valores_previos.get("Primario"):
            valores_prev_primario = [v.strip() for v in valores_previos["Primario"].split("+") if v.strip()]
        seleccion["Primario"] = st.multiselect(
            "Primario",
            options=opciones.get("Primaria", {}).get("valores", []),
            default=valores_prev_primario,
            format_func=lambda x: opciones.get("Primaria", {}).get("etiquetas", {}).get(x, x),
            key="sel_primario"
        )
        # Guardar como texto concatenado
        if isinstance(seleccion["Primario"], list):
            seleccion["Primario"] = " + ".join(seleccion["Primario"])

    # --- Secundario ---
    with col3:
        seleccion["Secundario"] = st.selectbox(
            "Secundario",
            ["Seleccionar estructura"] + opciones.get("Secundaria", {}).get("valores", []),
            index=(["Seleccionar estructura"] + opciones.get("Secundaria", {}).get("valores", [])).index(
                valores_previos.get("Secundario", "Seleccionar estructura")
            ) if valores_previos.get("Secundario") in opciones.get("Secundaria", {}).get("valores", []) else 0,
            key="sel_secundario"
        )

    # --- Retenidas ---
    with col4:
        seleccion["Retenidas"] = st.selectbox(
            "Retenida",
            ["Seleccionar estructura"] + opciones.get("Retenidas", {}).get("valores", []),
            index=(["Seleccionar estructura"] + opciones.get("Retenidas", {}).get("valores", [])).index(
                valores_previos.get("Retenidas", "Seleccionar estructura")
            ) if valores_previos.get("Retenidas") in opciones.get("Retenidas", {}).get("valores", []) else 0,
            key="sel_retenidas"
        )

    # --- Aterrizaje ---
    with col5:
        seleccion["Conexiones a tierra"] = st.selectbox(
            "Aterrizaje",
            ["Seleccionar estructura"] + opciones.get("Conexiones a tierra", {}).get("valores", []),
            index=(["Seleccionar estructura"] + opciones.get("Conexiones a tierra", {}).get("valores", [])).index(
                valores_previos.get("Conexiones a tierra", "Seleccionar estructura")
            ) if valores_previos.get("Conexiones a tierra") in opciones.get("Conexiones a tierra", {}).get("valores", []) else 0,
            key="sel_tierra"
        )

    # --- Transformadores ---
    with col6:
        seleccion["Transformadores"] = st.selectbox(
            "Transformador",
            ["Seleccionar estructura"] + opciones.get("Transformadores", {}).get("valores", []),
            index=(["Seleccionar estructura"] + opciones.get("Transformadores", {}).get("valores", [])).index(
                valores_previos.get("Transformadores", "Seleccionar estructura")
            ) if valores_previos.get("Transformadores") in opciones.get("Transformadores", {}).get("valores", []) else 0,
            key="sel_transformador"
        )

    return seleccion
