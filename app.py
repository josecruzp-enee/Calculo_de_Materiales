# app.py
# -*- coding: utf-8 -*-
"""
Aplicación Streamlit para:
1. Subir Excel del proyecto (estructuras_lista.xlsx)
2. Usar base de datos de materiales interna (Estructura_datos.xlsx)
3. Procesar materiales con reglas de reemplazo
4. Exportar resúmenes en Excel y PDF
"""

import streamlit as st
import pandas as pd
from io import BytesIO
import tempfile
import os
from openpyxl.utils import get_column_letter

# === Importar módulos propios ===
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


# ================== CONFIG STREAMLIT ==================
st.set_page_config(page_title="Cálculo de Materiales", layout="wide")
st.title("⚡ Cálculo de Materiales para Proyecto de Distribución")

# Columnas base para DataFrame
columnas = ["Punto", "Poste", "Primario", "Secundario", "Retenida", "Aterrizaje", "Transformador"]

# === Función para formulario edición de datos del proyecto ===
# === Función para formulario edición de datos del proyecto ===
import streamlit as st

# Función formulario que guarda en session_state
def formulario_datos_proyecto():
    st.subheader("📝 Datos del Proyecto (Formulario)")

    # Obtener datos actuales de session_state o valores vacíos
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

    with st.form("form_datos_proyecto", clear_on_submit=False):
        nombre_proyecto = st.text_input("Nombre del Proyecto", value=datos.get("nombre_proyecto", ""))
        codigo_proyecto = st.text_input("Código / Expediente", value=datos.get("codigo_proyecto", ""))
        nivel_tension = st.text_input("Nivel de Tensión (kV)", value=datos.get("nivel_de_tension", ""))
        calibre_primario = st.text_input("Calibre del Conductor de Media Tensión", value=datos.get("calibre_primario", ""))
        calibre_secundario = st.text_input("Calibre del Conductor de Baja Tensión", value=datos.get("calibre_secundario", ""))
        calibre_neutro = st.text_input("Calibre del Condcutor Neutro", value=datos.get("calibre_neutro", ""))
        calibre_piloto = st.text_input("Calibre del Conductor de Hilo Piloto", value=datos.get("calibre_piloto", ""))
        calibre_retenidas = st.text_input("Calibre del Cable de Retenida", value=datos.get("calibre_retenidas", ""))
        responsable = st.text_input("Responsable / Diseñador", value=datos.get("responsable", ""))
        empresa = st.text_input("Empresa / Área", value=datos.get("empresa", ""))

        submitted = st.form_submit_button("Guardar datos del proyecto")

        if submitted:
            # Actualizar session_state con los datos nuevos
            st.session_state["datos_proyecto"] = {
                "nombre_proyecto": nombre_proyecto,
                "codigo_proyecto": codigo_proyecto,
                "nivel_de_tension": nivel_tension,
                "calibre_primario": calibre_primario,
                "calibre_secundario": calibre_secundario,
                "calibre_neutro": calibre_neutro,
                "calibre_piloto": calibre_piloto,
                "calibre_retenidas": calibre_retenidas,
                "responsable": responsable,
                "empresa": empresa,
            }
            st.success("✅ Datos del proyecto actualizados")

# Función para mostrar datos formateados
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
            "calibre_neutro": "Calibre del Condcutor Neutro",
            "calibre_piloto": "Calibre del Conductor de Hilo Piloto",
            "calibre_retenidas": "Calibre del Cable de Retenida",
            "responsable": "Responsable / Diseñador",
            "empresa": "Empresa / Área",
        }
        for key, label in etiquetas_mostrar.items():
            st.markdown(f"**{label}:** {datos.get(key, '')}")


# === Función para mostrar datos en JSON ===
def mostrar_info_proyecto(datos_proyecto):
    st.subheader("📑 Datos del Proyecto Actualizados")
    st.json(datos_proyecto)

# === Función para guardar archivo temporal ===
def guardar_archivo_temporal(archivo_subido):
    temp_dir = tempfile.mkdtemp()
    ruta_temp = os.path.join(temp_dir, archivo_subido.name)
    with open(ruta_temp, "wb") as f:
        f.write(archivo_subido.getbuffer())
    return ruta_temp


# ================== FLUJO PRINCIPAL ==================
archivo_estructuras = st.file_uploader("📌 Archivo de estructuras (estructuras_lista.xlsx)", type=["xlsx"])

if archivo_estructuras:
    ruta_estructuras = guardar_archivo_temporal(archivo_estructuras)

    # Cargar datos del proyecto desde el archivo Excel
    try:
        datos_proyecto = cargar_datos_proyecto(ruta_estructuras)
    except Exception as e:
        st.warning(f"⚠️ No se pudo leer datos del proyecto: {e}")
        datos_proyecto = {}

    formulario_datos_proyecto()
    mostrar_datos_formateados()

    
    # === Leer estructuras proyectadas ===
    try:
        df = cargar_estructuras_proyectadas(ruta_estructuras)
        st.success("✅ Hoja 'estructuras' leída correctamente")
    except Exception as e:
        st.error(f"❌ No se pudo leer la hoja 'estructuras': {e}")
        st.stop()

    # Guardar en sesión para mantener el estado
    st.session_state["df_puntos"] = df.copy()

    # ================== EDITOR DE TABLA ==================
    df = st.data_editor(
        st.session_state.get("df_puntos", pd.DataFrame(columns=columnas)),
        num_rows="dynamic",
        use_container_width=True,
    )
    st.session_state["df_puntos"] = df

    # Vista previa
    st.subheader("📑 Vista previa de la tabla")
    st.dataframe(df, use_container_width=True)

    # ================== EXPORTAR TABLA ==================
    st.subheader("📥 Exportar tabla")

    # Exportar a CSV
    st.download_button(
        "⬇️ Descargar CSV",
        df.to_csv(index=False).encode("utf-8"),
        "estructuras_lista.csv",
        "text/csv"
    )

    # Exportar a Excel con ajuste de ancho de columnas
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

    # ================== GENERAR PDFs ==================
    st.subheader("📑 Exportar a PDF")

    try:
        # Aquí usas los datos_proyecto actualizados (desde formulario o archivo)
        df_resumen, df_estructuras_resumen, df_resumen_por_punto, datos_proyecto = procesar_materiales(
            ruta_estructuras, os.path.join("modulo", "Estructura_datos.xlsx")
        )

        st.download_button(
            "📄 Descargar PDF de Materiales",
            generar_pdf_materiales(df_resumen, datos_proyecto.get("nombre_proyecto", "Proyecto"), datos_proyecto),
            "Resumen_Materiales.pdf",
            "application/pdf"
        )

        st.download_button(
            "📄 Descargar PDF de Estructuras",
            generar_pdf_estructuras(df_estructuras_resumen, datos_proyecto.get("nombre_proyecto", "Proyecto")),
            "Resumen_Estructuras.pdf",
            "application/pdf"
        )

        st.download_button(
            "📄 Descargar PDF Materiales por Punto",
            generar_pdf_materiales_por_punto(df_resumen_por_punto, datos_proyecto.get("nombre_proyecto", "Proyecto")),
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

else:
    st.warning("⚠️ Debes subir el archivo de estructuras.")




