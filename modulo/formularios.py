# modulo/formulario.py
import streamlit as st
from modulo.calibres import cargar_calibres_desde_excel, seleccionar_calibres_formulario

# ================= FUNCIONES FORMULARIO =================

def obtener_datos_proyecto_defecto():
    """
    Devuelve un diccionario con valores por defecto para el proyecto.
    """
    return {
        "nombre_proyecto": "",
        "codigo_proyecto": "",
        "nivel_de_tension": "",
        "calibre_primario": "",
        "calibre_secundario": "",
        "calibre_neutro": "",
        "calibre_piloto": "",
        "calibre_retenidas": "",
        "responsable": "",
        "empresa": "",
    }

def seleccionar_nivel_tension(datos_proyecto, opciones_tension=None):
    """
    Muestra un selectbox para seleccionar el nivel de tensión.
    """
    if opciones_tension is None:
        opciones_tension = ["13.8", "34.5"]  # ajustar según la red

    valor_actual = datos_proyecto.get("nivel_de_tension", "")
    index = opciones_tension.index(valor_actual) if valor_actual in opciones_tension else 0
    nivel_tension = st.selectbox("Nivel de Tensión (KV)", opciones_tension, index=index)
    return nivel_tension

def formulario_datos_proyecto():
    """
    Formulario completo para capturar datos del proyecto.
    Incluye: nombre, código, nivel de tensión, calibres y responsable/empresa.
    """
    st.subheader("📝 Datos del Proyecto")

    # Cargar datos previos o por defecto
    datos = st.session_state.get("datos_proyecto", obtener_datos_proyecto_defecto())

    # Nivel de tensión
    nivel_tension = seleccionar_nivel_tension(datos)

    # Selección de calibres
    calibres = cargar_calibres_desde_excel()
    calibres_seleccionados = seleccionar_calibres_formulario(datos, calibres)

    # Campos de texto
    nombre = st.text_input("Nombre del Proyecto", value=datos.get("nombre_proyecto", ""))
    codigo = st.text_input("Código / Expediente", value=datos.get("codigo_proyecto", ""))
    responsable = st.text_input("Responsable / Diseñador", value=datos.get("responsable", ""))
    empresa = st.text_input("Empresa / Área", value=datos.get("empresa", ""))

    # Guardar todo en session_state
    st.session_state["datos_proyecto"] = {
        "nombre_proyecto": nombre,
        "codigo_proyecto": codigo,
        "nivel_de_tension": nivel_tension,
        **calibres_seleccionados,
        "responsable": responsable,
        "empresa": empresa,
    }

def mostrar_datos_formateados():
    """
    Muestra los datos del proyecto formateados en Streamlit.
    """
    datos = st.session_state.get("datos_proyecto", {})
    st.subheader("📑 Datos del Proyecto Actualizados")
    for k, v in datos.items():
        st.markdown(f"**{k}:** {v}")
