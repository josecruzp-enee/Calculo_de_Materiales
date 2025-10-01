# app.py
# -*- coding: utf-8 -*-
"""
Aplicación Streamlit para:
1. Subir Excel del proyecto y estructuras
2. Procesar materiales con reglas de reemplazo
3. Exportar resúmenes en Excel y PDF
"""

import streamlit as st
import pandas as pd
from io import BytesIO
import tempfile, os
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
from principal_materiales import procesar_materiales


# ================== CONFIG STREAMLIT ==================
st.set_page_config(page_title="Cálculo de Materiales", layout="wide")
st.title("⚡ Cálculo de Materiales para Proyecto de Distribución")

# Columnas base
columnas = ["Punto", "Poste", "Primario", "Secundario", "Retenida", "Aterrizaje", "Transformador"]

# ================== SUBIR ARCHIVO ==================
archivo_excel = st.file_uploader("📂 Sube el archivo Excel de estructuras", type=["xlsx"])

if archivo_excel:
    # Guardar archivo temporal
    temp_dir = tempfile.mkdtemp()
    ruta_temp = os.path.join(temp_dir, archivo_excel.name)
    with open(ruta_temp, "wb") as f:
        f.write(archivo_excel.getbuffer())

    # === Leer datos del proyecto ===
    try:
        datos_proyecto = cargar_datos_proyecto(ruta_temp)
        st.subheader("📑 Datos del Proyecto")
        st.json(datos_proyecto)
    except Exception as e:
        st.error(f"❌ No se pudo leer la hoja 'datos_proyecto': {e}")
        datos_proyecto = {}

    # === Leer estructuras proyectadas ===
    try:
        df = cargar_estructuras_proyectadas(ruta_temp)
        st.success("✅ Hoja 'estructuras' leída correctamente")
    except Exception as e:
        st.error(f"❌ No se pudo leer la hoja 'estructuras': {e}")
        st.stop()

    # Guardar en sesión
    st.session_state["df_puntos"] = df.copy()

else:
    st.info("ℹ️ No subiste archivo, puedes crear/editar la tabla directamente aquí abajo")
    if "df_puntos" not in st.session_state:
        st.session_state["df_puntos"] = pd.DataFrame(columns=columnas)


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


# ================== GENERAR PDFs ==================
st.subheader("📑 Exportar a PDF")

if archivo_excel:
    try:
        # Procesar materiales usando la misma lógica del script principal
        df_resumen, df_estructuras_resumen, df_resumen_por_punto, datos_proyecto = procesar_materiales(
            ruta_temp, "Estructura_datos.xlsx"  # Excel subido + base de datos
        )

        # PDF Materiales
        st.download_button(
            "📄 Descargar PDF de Materiales",
            generar_pdf_materiales(df_resumen, datos_proyecto.get("nombre_proyecto", "Proyecto"), datos_proyecto),
            "Resumen_Materiales.pdf",
            "application/pdf"
        )

        # PDF Estructuras
        st.download_button(
            "📄 Descargar PDF de Estructuras",
            generar_pdf_estructuras(df_estructuras_resumen, datos_proyecto.get("nombre_proyecto", "Proyecto")),
            "Resumen_Estructuras.pdf",
            "application/pdf"
        )

        # PDF Materiales por punto
        st.download_button(
            "📄 Descargar PDF Materiales por Punto",
            generar_pdf_materiales_por_punto(df_resumen_por_punto, datos_proyecto.get("nombre_proyecto", "Proyecto")),
            "Materiales_por_Punto.pdf",
            "application/pdf"
        )

        # PDF Completo
        st.download_button(
            "📄 Descargar Informe Completo (PDF)",
            generar_pdf_completo(df_resumen, df_estructuras_resumen, df_resumen_por_punto, datos_proyecto),
            "Informe_Completo.pdf",
            "application/pdf"
        )
    except Exception as e:
        st.error(f"⚠️ Error al procesar materiales: {e}")

