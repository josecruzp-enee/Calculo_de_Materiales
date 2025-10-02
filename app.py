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
def formulario_datos_proyecto(datos_proyecto=None):
    st.subheader("📝 Datos del Proyecto (Formulario)")

    with st.form("form_datos_proyecto", clear_on_submit=False):
        nombre_proyecto = st.text_input("Nombre del Proyecto", value=datos_proyecto.get("nombre_proyecto", "") if datos_proyecto else "")
        codigo_proyecto = st.text_input("Código / Expediente", value=datos_proyecto.get("codigo_proyecto", "") if datos_proyecto else "")
        nivel_tension = st.text_input("Nivel de Tensión (kV)", value=datos_proyecto.get("nivel_de_tension", "") if datos_proyecto else "")
        calibre_primario = st.text_input("Calibre del Conductor de Media Tensión", value=datos_proyecto.get("calibre_primario", "") if datos_proyecto else "")
        calibre_secundario = st.text_input("Calibre del Conductor Secundario", value=datos_proyecto.get("calibre_secundario", "") if datos_proyecto else "")
        calibre_neutro = st.text_input("Calibre del Neutro", value=datos_proyecto.get("calibre_neutro", "") if datos_proyecto else "")
        calibre_piloto = st.text_input("Calibre del Piloto", value=datos_proyecto.get("calibre_piloto", "") if datos_proyecto else "")
        calibre_retenidas = st.text_input("Calibre del Cable de Retenidas", value=datos_proyecto.get("calibre_retenidas", "") if datos_proyecto else "")
        responsable = st.text_input("Responsable / Diseñador", value=datos_proyecto.get("responsable", "") if datos_proyecto else "")
        empresa = st.text_input("Empresa / Área", value=datos_proyecto.get("empresa", "") if datos_proyecto else "")

        submitted = st.form_submit_button("Guardar datos del proyecto")

        if submitted:
            datos_nuevos = {
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
            return datos_nuevos

    # Si no se envió el formulario, devolver los datos que entraron (o vacíos)
    return datos_proyecto or {}

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

    # Mostrar el formulario para editar los datos del proyecto
    datos_proyecto = formulario_datos_proyecto(datos_proyecto)

    # Mostrar datos actuales en JSON (puedes cambiar a tabla o PDF si prefieres)
    mostrar_info_proyecto(datos_proyecto)

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
