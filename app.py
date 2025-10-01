# -*- coding: utf-8 -*-
"""
Created on Wed Oct  1 14:04:24 2025

@author: José Nikol Cruz
"""

# app.py
import streamlit as st
import pandas as pd
from io import BytesIO
from openpyxl.utils import get_column_letter

st.set_page_config(page_title="Gestión de Estructuras", layout="wide")

st.title("⚡ Gestión de Estructuras por Punto")

# Columnas base de la tabla
columnas = ["Punto", "Poste", "Primario", "Secundario", "Retenida", "Aterrizaje", "Transformador"]

# --- Opción 1: subir Excel ---
archivo_excel = st.file_uploader("📂 Sube el archivo Excel de estructuras", type=["xlsx", "csv"])

if archivo_excel:
    if archivo_excel.name.endswith(".xlsx"):
        df = pd.read_excel(archivo_excel)
    else:
        df = pd.read_csv(archivo_excel)

    # Validar que tenga las columnas necesarias
    if not all(col in df.columns for col in columnas):
        st.error(f"❌ El archivo debe contener las columnas: {', '.join(columnas)}")
        st.stop()

    st.success("✅ Archivo cargado correctamente")
    # Guardar en sesión para edición en vivo
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

# --- Botones de descarga ---
st.subheader("📥 Exportar tabla")

# Exportar a CSV
st.download_button(
    "⬇️ Descargar CSV",
    df.to_csv(index=False).encode("utf-8"),
    "estructuras_lista.csv",
    "text/csv"
)

# Exportar a Excel con ajuste automático de columnas
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
