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
import tempfile
import os
from openpyxl.utils import get_column_letter

from modulo.entradas import (
    cargar_datos_proyecto,
    cargar_estructuras_proyectadas,
)
from modulo.pdf_utils import (
    generar_pdf_materiales,
    generar_pdf_estructuras,
    generar_pdf_materiales_por_punto,
    generar_pdf_completo,
)
from modulo.procesar_materiales import procesar_materiales
from modulo.calibres import cargar_calibres_desde_excel, seleccionar_calibres_formulario


COLUMNAS_BASE = ["Punto", "Poste", "Primario", "Secundario", "Retenida", "Aterrizaje", "Transformador"]


# ================= FUNCIONES AUXILIARES =================

def formulario_datos_proyecto():
    st.subheader("📝 Datos del Proyecto (Formulario)")

    datos = st.session_state.get("datos_proyecto", {
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
    })

    calibres = cargar_calibres_desde_excel()

    with st.form("form_datos_proyecto", clear_on_submit=False):
        nombre_proyecto = st.text_input("Nombre del Proyecto", value=datos.get("nombre_proyecto", ""))
        codigo_proyecto = st.text_input("Código / Expediente", value=datos.get("codigo_proyecto", ""))
        nivel_tension = st.text_input("Nivel de Tensión (kV)", value=datos.get("nivel_de_tension", ""))
        
        calibres_seleccionados = seleccionar_calibres_formulario(datos, calibres)

        responsable = st.text_input("Responsable / Diseñador", value=datos.get("responsable", ""))
        empresa = st.text_input("Empresa / Área", value=datos.get("empresa", ""))

        submitted = st.form_submit_button("Guardar datos del proyecto")

        if submitted:
            st.session_state["datos_proyecto"] = {
                "nombre_proyecto": nombre_proyecto,
                "codigo_proyecto": codigo_proyecto,
                "nivel_de_tension": nivel_tension,
                **calibres_seleccionados,
                "responsable": responsable,
                "empresa": empresa,
            }
            st.success("✅ Datos del proyecto actualizados")


def mostrar_datos_formateados():
    datos = st.session_state.get("datos_proyecto")
    if datos:
        st.subheader("📑 Datos del Proyecto Actualizados")
        etiquetas_mostrar = {
            "nombre_proyecto": "Nombre del Proyecto",
            "codigo_proyecto": "Código / Expediente",
            "nivel_de_tension": "Nivel de Tensión (kV)",
            "calibre_primario": "Calibre del Conductor de Media Tensión",
            "calibre_secundario": "Calibre del Conductor de Baja Tensión",
            "calibre_neutro": "Calibre del Conductor Neutro",
            "calibre_piloto": "Calibre del Conductor de Hilo Piloto",
            "calibre_retenidas": "Calibre del Cable de Retenida",
            "responsable": "Responsable / Diseñador",
            "empresa": "Empresa / Área",
        }
        for key, label in etiquetas_mostrar.items():
            st.markdown(f"**{label}:** {datos.get(key, '')}")


def guardar_archivo_temporal(archivo_subido):
    temp_dir = tempfile.mkdtemp()
    ruta_temp = os.path.join(temp_dir, archivo_subido.name)
    with open(ruta_temp, "wb") as f:
        f.write(archivo_subido.getbuffer())
    return ruta_temp


def pegar_texto_a_df(texto, columnas):
    try:
        df = pd.read_csv(BytesIO(texto.encode()), sep=None, engine='python')
        df = df[[col for col in columnas if col in df.columns]]
        return df
    except Exception as e:
        st.error(f"Error al convertir texto pegado a tabla: {e}")
        return pd.DataFrame(columns=columnas)


def generar_pdfs(modo_carga, ruta_estructuras, df, ruta_datos_materiales="modulo/Estructura_datos.xlsx"):
    try:
        archivo_estructuras = None if modo_carga in ["Pegar tabla", "Listas desplegables"] else ruta_estructuras

        df_resumen, df_estructuras_resumen, df_resumen_por_punto, datos_proyecto = procesar_materiales(
            archivo_estructuras,
            ruta_datos_materiales,
            estructuras_df=df
        )

        nombre_proyecto = datos_proyecto.get("nombre_proyecto", "Proyecto") if datos_proyecto else "Proyecto"

        st.download_button(
            "📄 Descargar PDF de Materiales",
            generar_pdf_materiales(df_resumen, nombre_proyecto, datos_proyecto),
            "Resumen_Materiales.pdf",
            "application/pdf"
        )
        st.download_button(
            "📄 Descargar PDF de Estructuras",
            generar_pdf_estructuras(df_estructuras_resumen, nombre_proyecto),
            "Resumen_Estructuras.pdf",
            "application/pdf"
        )
        st.download_button(
            "📄 Descargar PDF Materiales por Punto",
            generar_pdf_materiales_por_punto(df_resumen_por_punto, nombre_proyecto),
            "Materiales_por_Punto.pdf",
            "application/pdf"
        )
        st.download_button(
            "📄 Descargar Informe Completo (PDF)",
            generar_pdf_completo(df_resumen, df_estructuras_resumen, df_resumen_por_punto, datos_proyecto),
            "Informe_Completo.pdf",
            "application/pdf"
        )

    except Exception as e:
        st.error(f"⚠️ Error al procesar materiales: {e}")


# ================= MAIN APP =================

def main():
    st.set_page_config(page_title="Cálculo de Materiales", layout="wide")
    st.title("⚡ Cálculo de Materiales para Proyecto de Distribución")

    if "datos_proyecto" not in st.session_state:
        st.session_state["datos_proyecto"] = {}

    st.subheader("Carga de estructuras proyectadas")
    modo_carga = st.selectbox(
        "Selecciona modo de carga:",
        ["Desde archivo Excel", "Pegar tabla", "Listas desplegables"]
    )

    df = pd.DataFrame(columns=COLUMNAS_BASE)
    ruta_estructuras = None

    # --- MODO 1: Excel ---
    if modo_carga == "Desde archivo Excel":
        archivo_estructuras = st.file_uploader("📌 Archivo de estructuras (estructuras_lista.xlsx)", type=["xlsx"])
        if archivo_estructuras:
            ruta_estructuras = guardar_archivo_temporal(archivo_estructuras)
            try:
                datos_proyecto = cargar_datos_proyecto(ruta_estructuras)
            except Exception as e:
                st.warning(f"⚠️ No se pudo leer datos del proyecto: {e}")
                datos_proyecto = {}

            if not st.session_state["datos_proyecto"]:
                st.session_state["datos_proyecto"] = datos_proyecto

            formulario_datos_proyecto()
            mostrar_datos_formateados()

            try:
                df = cargar_estructuras_proyectadas(ruta_estructuras)
                st.success("✅ Hoja 'estructuras' leída correctamente")
            except Exception as e:
                st.error(f"❌ No se pudo leer la hoja 'estructuras': {e}")
                st.stop()

    # --- MODO 2: Pegar tabla ---
    elif modo_carga == "Pegar tabla":
        st.info("Pega la tabla con columnas: Punto, Poste, Primario, Secundario, Retenida, Aterrizaje, Transformador")
        texto_pegado = st.text_area("Pega aquí tu tabla (CSV o tabulado)", height=200)
        if texto_pegado:
            df = pegar_texto_a_df(texto_pegado, COLUMNAS_BASE)
            st.success(f"✅ Tabla cargada con {len(df)} filas")
        formulario_datos_proyecto()
        mostrar_datos_formateados()

    # --- MODO 3: Listas desplegables ---
    elif modo_carga == "Listas desplegables":
        from modulo.desplegables import cargar_opciones, crear_desplegables

        opciones = cargar_opciones()

        if "df_puntos" not in st.session_state:
            st.session_state["df_puntos"] = pd.DataFrame(columns=COLUMNAS_BASE)

        st.subheader("➕ Agregar punto con desplegables")
        seleccion = crear_desplegables(opciones)

        if st.button("Agregar fila"):
            st.session_state["df_puntos"] = pd.concat(
                [st.session_state["df_puntos"], pd.DataFrame([seleccion])],
                ignore_index=True
            )
            st.success("✅ Fila agregada")

        df = st.session_state["df_puntos"]

        st.subheader("📑 Vista previa de la tabla")
        st.dataframe(df, use_container_width=True)

        formulario_datos_proyecto()
        mostrar_datos_formateados()

    # --- CONTINUA IGUAL EN LOS 3 MODOS ---
    if not df.empty:
        st.session_state["df_puntos"] = df.copy()

        df = st.data_editor(
            st.session_state.get("df_puntos", pd.DataFrame(columns=COLUMNAS_BASE)),
            num_rows="dynamic",
            use_container_width=True,
        )
        st.session_state["df_puntos"] = df

        st.subheader("📥 Exportar tabla")

        st.download_button(
            "⬇️ Descargar CSV",
            df.to_csv(index=False).encode("utf-8"),
            "estructuras_lista.csv",
            "text/csv"
        )

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Estructuras")
            ws = writer.sheets["Estructuras"]
            for col_idx, col in enumerate(df.columns, 1):
                max_length = max(df[col].astype(str).map(len).max(), len(col)) + 2
                ws.column_dimensions[get_column_letter(col_idx)].width = max_length

        st.download_button(
            "⬇️ Descargar Excel",
            output.getvalue(),
            "estructuras_lista.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.subheader("📑 Exportar a PDF")

        ruta_para_pdfs = ruta_estructuras if modo_carga == "Desde archivo Excel" else None
        generar_pdfs(modo_carga, ruta_para_pdfs, df)


if __name__ == "__main__":
    main()
