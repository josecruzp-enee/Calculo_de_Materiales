# app.py
import streamlit as st
import pandas as pd
from io import BytesIO

from modulo.utils import guardar_archivo_temporal, pegar_texto_a_df
from modulo.formularios import formulario_datos_proyecto, mostrar_datos_formateados
from modulo.procesar_materiales import procesar_materiales
from modulo.generar_pdfs import generar_pdfs
from modulo.calibres import cargar_calibres_desde_excel, seleccionar_calibres_formulario
from modulo.entradas import cargar_estructuras_proyectadas

COLUMNAS_BASE = ["Punto", "Poste", "Primario", "Secundario", "Retenida", "Aterrizaje", "Transformador"]

def main():
    st.set_page_config(page_title="Cálculo de Materiales", layout="wide")
    st.title("⚡ Cálculo de Materiales para Proyecto de Distribución")

    # 1️⃣ Modo de carga
    modo_carga = st.radio("Selecciona modo de carga:", ["Desde archivo Excel", "Pegar tabla", "Listas desplegables"])

    # 2️⃣ Nivel de tensión
    if "datos_proyecto" not in st.session_state:
        st.session_state["datos_proyecto"] = {}
    st.session_state["datos_proyecto"]["nivel_de_tension"] = st.text_input(
        "Nivel de Tensión (kV)",
        value=st.session_state["datos_proyecto"].get("nivel_de_tension", "")
    )

    # 3️⃣ Calibres
    calibres = cargar_calibres_desde_excel()
    calibres_seleccionados = seleccionar_calibres_formulario(st.session_state["datos_proyecto"], calibres)
    st.session_state["datos_proyecto"].update(calibres_seleccionados)

    # 4️⃣ Datos de proyecto
    formulario_datos_proyecto()
    mostrar_datos_formateados()

    # 5️⃣ Cargar estructuras
    df = pd.DataFrame(columns=COLUMNAS_BASE)
    ruta_estructuras = None

    if modo_carga == "Desde archivo Excel":
        archivo_estructuras = st.file_uploader("Archivo de estructuras", type=["xlsx"])
        if archivo_estructuras:
            ruta_estructuras = guardar_archivo_temporal(archivo_estructuras)
            df = cargar_estructuras_proyectadas(ruta_estructuras)

    elif modo_carga == "Pegar tabla":
        texto_pegado = st.text_area("Pega aquí tu tabla CSV/tabulado", height=200)
        if texto_pegado:
            df = pegar_texto_a_df(texto_pegado, COLUMNAS_BASE)

    elif modo_carga == "Listas desplegables":
        from modulo.desplegables import cargar_opciones, crear_desplegables
        opciones = cargar_opciones()
        seleccion = crear_desplegables(opciones)
        if st.button("Agregar fila"):
            st.session_state["df_puntos"] = pd.concat(
                [st.session_state.get("df_puntos", pd.DataFrame(columns=COLUMNAS_BASE)), pd.DataFrame([seleccion])],
                ignore_index=True
            )
        df = st.session_state.get("df_puntos", pd.DataFrame(columns=COLUMNAS_BASE))

    # 6️⃣ Exportación
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        generar_pdfs(modo_carga, ruta_estructuras, df)

if __name__ == "__main__":
    main()



