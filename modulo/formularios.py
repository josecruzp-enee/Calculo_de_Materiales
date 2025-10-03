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
    Formulario dividido en dos secciones:
    1. Información general del proyecto
    2. Selección de calibres de conductores
    """
    st.subheader("1. 📝 Datos del Proyecto")

    # Cargar datos previos o por defecto
    datos = st.session_state.get("datos_proyecto", obtener_datos_proyecto_defecto())

    # ---------------- SECCIÓN 1: INFO GENERAL ----------------
   
    nombre = st.text_input("Nombre del Proyecto", value=datos.get("nombre_proyecto", ""))
    codigo = st.text_input("Código / Expediente", value=datos.get("codigo_proyecto", ""))
    responsable = st.text_input("Responsable / Diseñador", value=datos.get("responsable", ""))
    empresa = st.text_input("Empresa / Área", value=datos.get("empresa", ""))
    nivel_tension = seleccionar_nivel_tension(datos)

    st.divider()

    # ---------------- SECCIÓN 2: CALIBRES ----------------
    st.markdown(" ### 2. 🧵 Selección de Calibres")
    calibres = cargar_calibres_desde_excel()
    calibres_seleccionados = seleccionar_calibres_formulario(datos, calibres)

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
    Muestra los datos del proyecto formateados en Streamlit en dos columnas.
    """
    datos = st.session_state.get("datos_proyecto", {})
    st.subheader("3. 📑 Datos del Proyecto Actualizados")

    col1, col2 = st.columns(2)

    # -------- Columna izquierda: info general --------
    with col1:
        st.markdown("**📌 Información General**")
        st.markdown(f"- **Nombre del Proyecto:** {datos.get('nombre_proyecto','')}")
        st.markdown(f"- **Código / Expediente:** {datos.get('codigo_proyecto','')}")
        st.markdown(f"- **Nivel de Tensión (kV):** {datos.get('nivel_de_tension','')}")
        st.markdown(f"- **Responsable / Diseñador:** {datos.get('responsable','')}")
        st.markdown(f"- **Empresa / Área:** {datos.get('empresa','')}")

    # -------- Columna derecha: calibres --------
    with col2:
        st.markdown("**🧵 Calibres Seleccionados**")
        st.markdown(f"- **Conductor Primario:** {datos.get('calibre_primario','')}")
        st.markdown(f"- **Conductor Secundario:** {datos.get('calibre_secundario','')}")
        st.markdown(f"- **Neutro:** {datos.get('calibre_neutro','')}")
        st.markdown(f"- **Hilo Piloto:** {datos.get('calibre_piloto','')}")
        st.markdown(f"- **Cable de Retenida:** {datos.get('calibre_retenidas','')}")
