# app.py
import streamlit as st
import pandas as pd
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

    # Inicialización de sesión
    if "datos_proyecto" not in st.session_state:
        st.session_state["datos_proyecto"] = {}

    # 2️⃣ Nivel de tensión (ejemplo lista desplegable)
    tensiones_disponibles = ["13.8", "34.5", "46"]
    valor_actual = st.session_state["datos_proyecto"].get("nivel_de_tension", "34.5")
    nivel_tension = st.selectbox("Nivel de Tensión (kV)", tensiones_disponibles,
                                 index=tensiones_disponibles.index(valor_actual) if valor_actual in tensiones_disponibles else 0)
    st.session_state["datos_proyecto"]["nivel_de_tension"] = nivel_tension

    # 3️⃣ Calibres
    calibres = cargar_calibres_desde_excel()
    calibres_seleccionados = seleccionar_calibres_formulario(st.session_state["datos_proyecto"], calibres)
    st.session_state["datos_proyecto"].update(calibres_seleccionados)

    # 4️⃣ Datos de proyecto
    formulario_datos_proyecto()
    mostrar_datos_formateados()

    # 5️⃣ Cargar estructuras y procesar
    df = pd.DataFrame(columns=COLUMNAS_BASE)
    ruta_estructuras = None
    # --- aquí agregas tu lógica de carga (Excel, texto, desplegables) ---

    # 6️⃣ Exportación
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        generar_pdfs(modo_carga, ruta_estructuras, df)

if __name__ == "__main__":
    main()
