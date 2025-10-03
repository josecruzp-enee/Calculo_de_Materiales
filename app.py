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
COLUMNAS_BASE = [
    "Punto", "Poste", "Primario", "Secundario",
    "Retenidas", "Conexiones a tierra", "Transformadores"
]

def main():
    st.set_page_config(page_title="Cálculo de Materiales", layout="wide")
    st.title("⚡ Cálculo de Materiales para Proyecto de Distribución")

    # ========================
    # 1️⃣ Modo de carga
    # ========================
    modo_carga = st.radio(
        "Selecciona modo de carga:",
        ["Desde archivo Excel", "Pegar tabla", "Listas desplegables"]
    )

    # Inicialización
    if "datos_proyecto" not in st.session_state:
        st.session_state["datos_proyecto"] = {}
    if "df_puntos" not in st.session_state:
        st.session_state["df_puntos"] = pd.DataFrame(columns=COLUMNAS_BASE)

    # ========================
    # 2️⃣ Datos del proyecto
    # ========================
    formulario_datos_proyecto()

    # ========================
    # 3️⃣ Mostrar resumen del proyecto
    # ========================
    mostrar_datos_formateados()

    # ========================
    # 4️⃣ Entrada de estructuras
    # ========================
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

        st.subheader("4. 🏗️ Estructuras del Proyecto")

        df_actual = st.session_state["df_puntos"]
        puntos_existentes = df_actual["Punto"].unique().tolist()

        # Crear nuevo punto
        if st.button("🆕 Crear nuevo Punto"):
            nuevo_num = len(puntos_existentes) + 1
            st.session_state["punto_en_edicion"] = f"Punto {nuevo_num}"
            st.success(f"✏️ {st.session_state['punto_en_edicion']} creado y listo para editar")

        # Seleccionar un punto existente
        if puntos_existentes:
            seleccionado = st.selectbox(
                "📍 Selecciona un Punto existente:",
                puntos_existentes,
                index=0
            )
            if st.button("✏️ Editar Punto seleccionado"):
                st.session_state["punto_en_edicion"] = seleccionado

        # Si hay punto en edición
        if "punto_en_edicion" in st.session_state:
            punto = st.session_state["punto_en_edicion"]
            st.markdown(f"### ✏️ Editando {punto}")
            seleccion = crear_desplegables(opciones)
            seleccion["Punto"] = punto

            # Guardar Punto
            if st.button("💾 Guardar Punto"):
                df_actual = df_actual[df_actual["Punto"] != punto]  # elimina versiones anteriores
                df_actual = pd.concat([df_actual, pd.DataFrame([seleccion])], ignore_index=True)

                # Ordenar puntos por número
                df_actual["orden"] = df_actual["Punto"].str.extract(r'(\d+)').astype(int)
                df_actual = df_actual.sort_values("orden").drop(columns="orden")
                st.session_state["df_puntos"] = df_actual.reset_index(drop=True)

                st.success(f"✅ {punto} guardado correctamente")
                st.session_state.pop("punto_en_edicion")  # salir de edición

        df = st.session_state["df_puntos"]

        # 👇 Vista previa dentro de la sección 4
        if not df.empty:
            st.markdown("#### 📑 Vista de estructuras / materiales")
            st.dataframe(df, use_container_width=True, hide_index=True)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🧹 Limpiar todo"):
                    st.session_state["df_puntos"] = pd.DataFrame(columns=COLUMNAS_BASE)
                    st.session_state.pop("punto_en_edicion", None)
                    st.success("✅ Se limpiaron todas las estructuras/materiales")

            with col2:
                punto_borrar = st.selectbox("❌ Seleccionar Punto a borrar", df["Punto"].unique())
                if st.button("Borrar Punto"):
                    st.session_state["df_puntos"] = df[df["Punto"] != punto_borrar].reset_index(drop=True)
                    st.success(f"✅ Se eliminó {punto_borrar}")

    # ========================
    # 5️⃣ Finalizar Cálculo
    # ========================
    if not df.empty:
        st.subheader("5. 🏁 Finalizar Cálculo del Proyecto")
        if st.button("✅ Finalizar Cálculo"):
            try:
                st.success("🎉 Cálculo finalizado con éxito. Ahora puedes exportar los reportes.")
            except Exception as e:
                st.error(f"❌ Error al finalizar cálculo: {e}")

    # ========================
    # 6️⃣ Exportación
    # ========================
    if not df.empty:
        st.subheader("6. 📂 Exportación de Reportes")
        generar_pdfs(modo_carga, ruta_estructuras, df)


if __name__ == "__main__":
    main()

