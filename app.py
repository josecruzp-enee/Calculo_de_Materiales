# app.py
# -*- coding: utf-8 -*-
"""
Gestión de estructuras y generación de reportes PDF
"""

import streamlit as st
import pandas as pd
from io import BytesIO
from openpyxl.utils import get_column_letter

# Importar funciones PDF
from modulo.pdf_utils import (
    generar_pdf_materiales,
    generar_pdf_estructuras,
    generar_pdf_materiales_por_punto,
    generar_pdf_completo
)

st.set_page_config(page_title="Cálculo de Materiales", layout="wide")

st.title("⚡ Cálculo de Materiales para Proyecto de Distribución")

# Columnas base de la tabla
columnas = ["Punto", "Poste", "Primario", "Secundario", "Retenida", "Aterrizaje", "Transformador"]

# --- Opción 1: subir Excel ---
archivo_excel = st.file_uploader("📂 Sube el archivo Excel de estructuras", type=["xlsx", "csv"])

if archivo_excel:
    if archivo_excel.name.endswith(".xlsx"):
        df = pd.read_excel(archivo_excel)
    else:
        df = pd.read_csv(archivo_excel)

    # Validar columnas
    if not all(col in df.columns for col in columnas):
        st.error(f"❌ El archivo debe contener las columnas: {', '.join(columnas)}")
        st.stop()

    st.success("✅ Archivo cargado correctamente")
    st.session_state["df_puntos"] = df.copy()
else:
    st.info("ℹ️ No subiste archivo, puedes crear/editar la tabla directamente aquí abajo")
    if "df_puntos" not in st.session_state:
        st.session_state["df_puntos"] = pd.DataFrame(columns=columnas)

    if st.button("🧹 Limpiar tabla"):
        st.session_state["df_puntos"] = pd.DataFrame(columns=columnas)
        st.rerun()

# --- Siempre trabajar con la sesión ---
df = st.data_editor(
    st.session_state.get("df_puntos", pd.DataFrame(columns=columnas)),
    num_rows="dynamic",
    use_container_width=True,
)
st.session_state["df_puntos"] = df

# Mostrar vista previa
st.subheader("📑 Vista previa de la tabla")
st.dataframe(df, use_container_width=True)

# --- Exportar tabla ---
st.subheader("📥 Exportar tabla")

# Exportar a CSV
st.download_button(
    "⬇️ Descargar CSV",
    df.to_csv(index=False).encode("utf-8"),
    "estructuras_lista.csv",
    "text/csv"
)

# Exportar a Excel
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

# --- Generación de PDFs ---
st.subheader("📑 Exportar a PDF")

nombre_proyecto = "Proyecto de Prueba"
datos_proyecto = {
    "nombre_proyecto": nombre_proyecto,
    "codigo_proyecto": "EXP-001",
    "nivel_de_tension": "13.8 kV",
    "calibre_primario": "4/0 AWG",
    "calibre_secundario": "2 AWG",
    "calibre_neutro": "1/0 AWG",
    "calibre_piloto": "N/A",
    "calibre_retenidas": "3/8\" AC",
    "responsable": "Ing. José Nikol Cruz",
    "empresa": "ENEE",
}

# PDF Materiales
pdf_buffer = generar_pdf_materiales(df, nombre_proyecto, datos_proyecto)
st.download_button(
    "📄 Descargar PDF de Materiales",
    pdf_buffer,
    "Resumen_Materiales.pdf",
    "application/pdf"
)

# PDF Estructuras
pdf_buffer = generar_pdf_estructuras(df, nombre_proyecto)
st.download_button(
    "📄 Descargar PDF de Estructuras",
    pdf_buffer,
    "Resumen_Estructuras.pdf",
    "application/pdf"
)

# PDF Materiales por punto
pdf_buffer = generar_pdf_materiales_por_punto(df, nombre_proyecto)
st.download_button(
    "📄 Descargar PDF Materiales por Punto",
    pdf_buffer,
    "Materiales_por_Punto.pdf",
    "application/pdf"
)

# PDF Completo
pdf_buffer = generar_pdf_completo(df, df, df, datos_proyecto)
st.download_button(
    "📄 Descargar Informe Completo (PDF)",
    pdf_buffer,
    "Informe_Completo.pdf",
    "application/pdf"
)



