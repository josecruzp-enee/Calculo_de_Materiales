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
from io import BytesIO

from modulo.utils import guardar_archivo_temporal, pegar_texto_a_df
from modulo.formularios import formulario_datos_proyecto, mostrar_datos_formateados
from modulo.procesar_materiales import procesar_materiales
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

    # 2️⃣ Formulario de datos del proyecto
    formulario_datos_proyecto()
    mostrar_datos_formateados()

    # 3️⃣ Cargar estructuras
    df = pd.DataFrame(columns=COLUMNAS_BASE)
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

    elif modo_carga == "Listas desplegables":
        from modulo.desplegables import cargar_opciones, crear_desplegables
        opciones = cargar_opciones()

        # 1️⃣ Detectar puntos ya creados
        df_actual = st.session_state.get("df_puntos", pd.DataFrame(columns=COLUMNAS_BASE))
        puntos_existentes = df_actual["Punto"].unique().tolist() if not df_actual.empty else []

        # 2️⃣ Mostrar puntos existentes
        punto_elegido = None
        if puntos_existentes:
            punto_elegido = st.selectbox("📍 Selecciona un Punto existente:", puntos_existentes)

        # 3️⃣ Botón para crear nuevo punto
        if st.button("➕ Crear nuevo Punto"):
            nuevo_num = len(puntos_existentes) + 1
            punto_elegido = f"Punto {nuevo_num}"

            df_nuevo = pd.DataFrame([{"Punto": punto_elegido,
                                      "Poste": None, "Primario": None, "Secundario": None,
                                      "Retenidas": None, "Conexiones a tierra": None,
                                      "Transformadores": None}])
            df_actual = pd.concat([df_actual, df_nuevo], ignore_index=True)
            st.session_state["df_puntos"] = df_actual
            st.success(f"✅ Se creó {punto_elegido}")

        # 4️⃣ Si hay un punto seleccionado → desplegables de estructuras
        if punto_elegido:
            st.markdown(f"### ✏️ Editando {punto_elegido}")
            seleccion = crear_desplegables(opciones)
            seleccion["Punto"] = punto_elegido

            if st.button("➕ Agregar materiales al Punto seleccionado"):
                df_combinado = pd.concat([df_actual, pd.DataFrame([seleccion])], ignore_index=True)

                # Consolidar si tiene Materiales y Cantidad
                if "Material" in df_combinado.columns and "Cantidad" in df_combinado.columns:
                    df_combinado = (
                        df_combinado.groupby(["Punto", "Material", "Unidad"], as_index=False)["Cantidad"]
                        .sum()
                    )

                st.session_state["df_puntos"] = df_combinado
                st.success(f"✅ Se actualizaron materiales en {punto_elegido}")

        df = st.session_state.get("df_puntos", pd.DataFrame(columns=COLUMNAS_BASE))

    # 4️⃣ Vista preliminar de datos
    if not df.empty:
        st.subheader("📑 Vista de estructuras / materiales")
        st.dataframe(df, use_container_width=True)

    # 5️⃣ Exportación
    if not df.empty:
        generar_pdfs(modo_carga, ruta_estructuras, df)

if __name__ == "__main__":
    main()
