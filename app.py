# app.py
# -*- coding: utf-8 -*-
"""
Aplicación Streamlit para:
1. Subir Excel del proyecto (estructuras_lista.xlsx)
2. Usar base de datos de materiales interna (Estructura_datos.xlsx)
3. Procesar materiales con reglas de reemplazo
4. Exportar resúmenes en Excel y PDF
5. Construir estructuras desde listas desplegables (índice)
"""

import streamlit as st
import pandas as pd

from modulo.utils import guardar_archivo_temporal, pegar_texto_a_df
from modulo.formularios import formulario_datos_proyecto, mostrar_datos_formateados
from modulo.generar_pdfs import generar_pdfs
from modulo.entradas import cargar_estructuras_proyectadas

# 👇 columnas base ajustadas a tu Excel
COLUMNAS_BASE = ["Punto", "Poste", "Primario", "Secundario", "Retenidas", "Conexiones a tierra", "Transformadores"]

def main():
    st.set_page_config(page_title="Cálculo de Materiales", layout="wide")
    st.title("⚡ Cálculo de Materiales para Proyecto de Distribución")

    # 1️⃣ Modo de carga
    modo_carga = st.radio(
        "Selecciona modo de carga:",
        ["Desde archivo Excel", "Pegar tabla", "Listas desplegables"]
    )

    # Inicialización de session_state
    if "datos_proyecto" not in st.session_state:
        st.session_state["datos_proyecto"] = {}
    if "df_puntos" not in st.session_state:
        st.session_state["df_puntos"] = pd.DataFrame(columns=COLUMNAS_BASE)
    if "punto_activo" not in st.session_state:
        st.session_state["punto_activo"] = None

    # 2️⃣ Formulario de datos del proyecto
    formulario_datos_proyecto()
    mostrar_datos_formateados()

    # 3️⃣ Cargar estructuras
    df = st.session_state["df_puntos"]
    ruta_estructuras = None

    if modo_carga == "Desde archivo Excel":
        archivo_estructuras = st.file_uploader("Archivo de estructuras", type=["xlsx"])
        if archivo_estructuras:
            ruta_estructuras = guardar_archivo_temporal(archivo_estructuras)
            try:
                df = cargar_estructuras_proyectadas(ruta_estructuras)
                st.success("✅ Hoja 'estructuras' leída correctamente")
            except Exception as e:
                st.error(f"❌ No se pudo leer la hoja 'estructuras': {e}")

    elif modo_carga == "Pegar tabla":
        texto_pegado = st.text_area("Pega aquí tu tabla CSV/tabulado", height=200)
        if texto_pegado:
            df = pegar_texto_a_df(texto_pegado, COLUMNAS_BASE)
            st.success(f"✅ Tabla cargada con {len(df)} filas")
            st.session_state["df_puntos"] = df

    elif modo_carga == "Listas desplegables":
        from modulo.desplegables import cargar_opciones, crear_desplegables
        opciones = cargar_opciones()

        # --------- Sección 4: Estructuras del Proyecto ---------
        st.subheader("4. 🏗️ Estructuras del Proyecto")

        df_actual = st.session_state["df_puntos"]
        puntos_existentes = df_actual["Punto"].unique().tolist() if not df_actual.empty else []

        # Crear nuevo punto
        if st.button("➕ Crear nuevo Punto"):
            nuevo_num = len(puntos_existentes) + 1
            st.session_state["punto_activo"] = f"Punto {nuevo_num}"

            df_nuevo = pd.DataFrame([{"Punto": st.session_state["punto_activo"],
                                      "Poste": None, "Primario": None, "Secundario": None,
                                      "Retenidas": None, "Conexiones a tierra": None,
                                      "Transformadores": None}])
            df_actual = pd.concat([df_actual, df_nuevo], ignore_index=True)
            st.session_state["df_puntos"] = df_actual
            st.success(f"✅ Se creó {st.session_state['punto_activo']} y está listo para editar")

        # Selección de punto
        if puntos_existentes:
            st.session_state["punto_activo"] = st.selectbox(
                "📍 Selecciona un Punto existente:",
                puntos_existentes,
                index=puntos_existentes.index(st.session_state["punto_activo"]) if st.session_state["punto_activo"] in puntos_existentes else 0
            )

        # Edición del punto activo
        if st.session_state["punto_activo"]:
            punto_elegido = st.session_state["punto_activo"]
            st.markdown(f"### ✏️ Editando {punto_elegido}")

            seleccion = crear_desplegables(opciones)
            seleccion["Punto"] = punto_elegido

            if st.button("💾 Guardar cambios en el Punto seleccionado"):
                df_nuevo = pd.DataFrame([seleccion])
                df_actual = df_actual[df_actual["Punto"] != punto_elegido]
                df_actual = pd.concat([df_actual, df_nuevo], ignore_index=True)
                st.session_state["df_puntos"] = df_actual
                st.success(f"✅ Se actualizaron los datos de {punto_elegido}")

        df = st.session_state["df_puntos"]

    # 4️⃣ Vista preliminar de datos + opciones de limpieza
    if not df.empty:
        st.subheader("📑 Vista de estructuras / materiales")
        st.dataframe(df, use_container_width=True)

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🧹 Limpiar todos los listados"):
                st.session_state["df_puntos"] = pd.DataFrame(columns=COLUMNAS_BASE)
                st.session_state["punto_activo"] = None
                st.success("✅ Se limpiaron todas las estructuras/materiales")

        with col2:
            if "Punto" in df.columns and not df.empty:
                st.markdown("### ❌ Borrar Punto")
                punto_borrar = st.selectbox("Selecciona el Punto a borrar", df["Punto"].unique())
                if st.button("🗑️ Borrar Punto seleccionado"):
                    df_filtrado = df[df["Punto"] != punto_borrar]
                    st.session_state["df_puntos"] = df_filtrado
                    if st.session_state["punto_activo"] == punto_borrar:
                        st.session_state["punto_activo"] = None
                    st.success(f"✅ Se eliminó {punto_borrar}")

    # 5️⃣ Exportación
    if not df.empty:
        generar_pdfs(modo_carga, ruta_estructuras, df)

if __name__ == "__main__":
    main()
