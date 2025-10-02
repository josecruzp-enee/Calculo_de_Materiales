import streamlit as st
from modulo.calibres import cargar_calibres_desde_excel, seleccionar_calibres_formulario

def formulario_datos_proyecto():
    st.subheader("📝 Datos del Proyecto")
    datos = st.session_state.get("datos_proyecto", {})
    nombre = st.text_input("Nombre del Proyecto", value=datos.get("nombre_proyecto",""))
    codigo = st.text_input("Código / Expediente", value=datos.get("codigo_proyecto",""))
    responsable = st.text_input("Responsable / Diseñador", value=datos.get("responsable",""))
    empresa = st.text_input("Empresa / Área", value=datos.get("empresa",""))
    st.session_state["datos_proyecto"].update({"nombre_proyecto":nombre,"codigo_proyecto":codigo,
                                               "responsable":responsable,"empresa":empresa})

def mostrar_datos_formateados():
    datos = st.session_state.get("datos_proyecto",{})
    for k,v in datos.items():
        st.markdown(f"**{k}:** {v}")
