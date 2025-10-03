# app.py
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd

from modulo.utils import guardar_archivo_temporal, pegar_texto_a_df
from modulo.formularios import formulario_datos_proyecto, mostrar_datos_formateados
from modulo.generar_pdfs import generar_pdfs
from modulo.entradas import cargar_estructuras_proyectadas

# 👇 columnas base ajustadas a tu Excel
COLUMNAS_BASE = [
    "Punto", "Poste", "Primario", "Secundario",
    "Retenidas", "Conexiones a tierra", "Transformadores"
]

# ========================
# Helpers
# ========================
def resetear_desplegables():
    """Resetea todos los selectbox de estructuras a 'Seleccionar estructura'."""
    for key in ["sel_poste", "sel_primario", "sel_secundario",
                "sel_retenidas", "sel_tierra", "sel_transformador"]:
        st.session_state[key] = "Seleccionar estructura"

# ========================
# Datos del proyecto
# ========================
def seccion_datos_proyecto():
    formulario_datos_proyecto()
    mostrar_datos_formateados()

# ========================
# Entrada de estructuras
# ========================
def seccion_entrada_estructuras(modo_carga):
    df = pd.DataFrame(columns=COLUMNAS_BASE)
    ruta_estructuras = None

    if modo_carga == "Desde archivo Excel":
        df, ruta_estructuras = cargar_desde_excel()

    elif modo_carga == "Pegar tabla":
        df = pegar_tabla()

    elif modo_carga == "Listas desplegables":
        df = listas_desplegables()

    return df, ruta_estructuras

def cargar_desde_excel():
    archivo_estructuras = st.file_uploader("Archivo de estructuras", type=["xlsx"])
    if archivo_estructuras:
        ruta_estructuras = guardar_archivo_temporal(archivo_estructuras)
        try:
            df = cargar_estructuras_proyectadas(ruta_estructuras)
            st.success("✅ Hoja 'estructuras' leída correctamente")
            return df, ruta_estructuras
        except Exception as e:
            st.error(f"❌ No se pudo leer la hoja 'estructuras': {e}")
    return pd.DataFrame(columns=COLUMNAS_BASE), None

def pegar_tabla():
    texto_pegado = st.text_area("Pega aquí tu tabla CSV/tabulado", height=200)
    if texto_pegado:
        df = pegar_texto_a_df(texto_pegado, COLUMNAS_BASE)
        st.success(f"✅ Tabla cargada con {len(df)} filas")
        return df
    return pd.DataFrame(columns=COLUMNAS_BASE)

def listas_desplegables():
    from modulo.desplegables import cargar_opciones, crear_desplegables
    opciones = cargar_opciones()

    st.subheader("4. 🏗️ Estructuras del Proyecto")

    df_actual = st.session_state["df_puntos"]
    puntos_existentes = df_actual["Punto"].unique().tolist()

    # Crear nuevo punto
    if st.button("🆕 Crear nuevo Punto"):
        nuevo_num = len(puntos_existentes) + 1
        st.session_state["punto_en_edicion"] = f"Punto {nuevo_num}"
        st.success(f"✏️ {st.session_state['punto_en_edicion']} creado y listo para editar")
        resetear_desplegables()

    # Seleccionar un punto existente
    if puntos_existentes:
        seleccionado = st.selectbox("📍 Selecciona un Punto existente:", puntos_existentes, index=0)
        if st.button("✏️ Editar Punto seleccionado"):
            st.session_state["punto_en_edicion"] = seleccionado
            resetear_desplegables()

    # Si hay punto en edición
    if "punto_en_edicion" in st.session_state:
        punto = st.session_state["punto_en_edicion"]
        st.markdown(f"### ✏️ Editando {punto}")
        seleccion = crear_desplegables(opciones)
        seleccion["Punto"] = punto

        if st.button("💾 Guardar Punto"):
            df_actual = df_actual[df_actual["Punto"] != punto]
            df_actual = pd.concat([df_actual, pd.DataFrame([seleccion])], ignore_index=True)

            # 👉 Ordenar puntos
            df_actual["orden"] = df_actual["Punto"].str.extract(r'(\d+)').astype(int)
            df_actual = df_actual.sort_values("orden").drop(columns="orden")
            st.session_state["df_puntos"] = df_actual.reset_index(drop=True)

            st.success(f"✅ {punto} guardado correctamente")
            resetear_desplegables()
            st.session_state.pop("punto_en_edicion")

    df = st.session_state["df_puntos"]

    # Vista previa
    if not df.empty:
        st.markdown("#### 📑 Vista de estructuras / materiales")
        st.dataframe(df, use_container_width=True, hide_index=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧹 Limpiar todo"):
                st.session_state["df_puntos"] = pd.DataFrame(columns=COLUMNAS_BASE)
                st.session_state.pop("punto_en_edicion", None)
                resetear_desplegables()
                st.success("✅ Se limpiaron todas las estructuras/materiales")
        with col2:
            punto_borrar = st.selectbox("❌ Seleccionar Punto a borrar", df["Punto"].unique())
            if st.button("Borrar Punto"):
                st.session_state["df_puntos"] = df[df["Punto"] != punto_borrar].reset_index(drop=True)
                st.success(f"✅ Se eliminó {punto_borrar}")

    return df

# ========================
# Finalizar cálculo
# ========================
def seccion_finalizar_calculo(df):
    if not df.empty:
        st.subheader("5. 🏁 Finalizar Cálculo del Proyecto")
        if st.button("✅ Finalizar Cálculo"):
            try:
                st.success("🎉 Cálculo finalizado con éxito. Ahora puedes exportar los reportes.")
            except Exception as e:
                st.error(f"❌ Error al finalizar cálculo: {e}")

# ========================
# Exportación
# ========================
def seccion_exportacion(df, modo_carga, ruta_estructuras):
    if not df.empty:
        st.subheader("6. 📂 Exportación de Reportes")
        generar_pdfs(modo_carga, ruta_estructuras, df)

# ========================
# MAIN
# ========================
def main():
    st.set_page_config(page_title="Cálculo de Materiales", layout="wide")
    st.title("⚡ Cálculo de Materiales para Proyecto de Distribución")

    modo_carga = st.radio("Selecciona modo de carga:", ["Desde archivo Excel", "Pegar tabla", "Listas desplegables"])

    if "datos_proyecto" not in st.session_state:
        st.session_state["datos_proyecto"] = {}
    if "df_puntos" not in st.session_state:
        st.session_state["df_puntos"] = pd.DataFrame(columns=COLUMNAS_BASE)

    seccion_datos_proyecto()
    df, ruta_estructuras = seccion_entrada_estructuras(modo_carga)
    seccion_finalizar_calculo(df)
    seccion_exportacion(df, modo_carga, ruta_estructuras)


if __name__ == "__main__":
    main()
