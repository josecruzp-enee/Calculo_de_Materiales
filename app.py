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

COLUMNAS_BASE = ["Punto", "Poste", "Primario", "Secundario", "Retenida", "Aterrizaje", "Transformador"]

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

    # 2️⃣ Formulario de datos del proyecto (tensión + calibres + responsable/empresa)
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
        seleccion = crear_desplegables(opciones)

        if st.button("Agregar Punto"):
            num_punto = len(st.session_state.get("df_puntos", [])) + 1
            seleccion["Punto"] = f"Punto {num_punto}"  # numeración automática
            st.session_state["df_puntos"] = pd.concat(
                [st.session_state.get("df_puntos", pd.DataFrame(columns=COLUMNAS_BASE)),
                 pd.DataFrame([seleccion])],
                ignore_index=True
            )
        df = st.session_state.get("df_puntos", pd.DataFrame(columns=COLUMNAS_BASE))

    # 4️⃣ Vista preliminar de datos
    if not df.empty:
        st.subheader("📑 Vista de estructuras")
        st.dataframe(df, use_container_width=True)

        # 5️⃣ Exportación
        # Agrupar estructuras repetidas
        df_agrupado = (
            df.groupby(
                ["Punto", "Poste", "Primario", "Secundario", "Retenida", "Aterrizaje", "Transformador"],
                as_index=False
            )
            .first()
        )

        # Agrupar materiales por Punto si existen esas columnas
        if "Material" in df.columns and "Cantidad" in df.columns:
            df_export = (
                df.groupby(["Punto", "Material", "Unidad"], as_index=False)["Cantidad"]
                  .sum()
            )
        else:
            df_export = df_agrupado

        # Generar PDFs
        if not df_export.empty:
            generar_pdfs(modo_carga, ruta_estructuras, df_export)
        else:
            st.warning("⚠️ No hay estructuras/materiales para exportar.")

if __name__ == "__main__":
    main()
