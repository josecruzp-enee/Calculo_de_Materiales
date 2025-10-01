# app.py
# -*- coding: utf-8 -*-
"""
Aplicación Streamlit para:
1. Subir Excel del proyecto (estructuras_lista.xlsx)
2. Subir base de datos de materiales (Estructura_datos.xlsx)
3. Procesar materiales con reglas de reemplazo
4. Exportar resúmenes en Excel y PDF
"""

import streamlit as st
import pandas as pd
from io import BytesIO
import tempfile, os
from openpyxl.utils import get_column_letter

# === Importar módulos propios ===
from modulos.entradas import (
    cargar_datos_proyecto,
    cargar_estructuras_proyectadas,
)
from modulos.pdf_utils import (
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

# ================== SUBIR ARCHIVOS ==================
st.subheader("📂 Sube los archivos necesarios")

archivo_estructuras = st.file_uploader("📌 Archivo de estructuras (estructuras_lista.xlsx)", type=["xlsx"])
archivo_materiales = st.file_uploader("📌 Base de datos de materiales (Estructura_datos.xlsx)", type=["xlsx"])

if archivo_estructuras and archivo_materiales:
    # Guardar archivos temporales
    temp_dir = tempfile.mkdtemp()

    ruta_estructuras = os.path.join(temp_dir, archivo_estructuras.name)
    with open(ruta_estructuras, "wb") as f:
        f.write(archivo_estructuras.getbuffer())

    ruta_materiales = os.path.join(temp_dir, archivo_materiales.name)
    with open(ruta_materiales, "wb") as f:
        f.write(archivo_materiales.getbuffer())

    # === Leer datos del proyecto ===
    try:
        datos_proyecto = cargar_datos_proyecto(ruta_estructuras)
        st.subheader("📑 Datos del Proyecto")
        st.json(datos_proyecto)
    except Exception as e:
        st.error(f"❌ No se pudo leer la hoja 'datos_proyecto': {e}")
        datos_proyecto = {}

    # === Leer estructuras proyectadas ===
    try:
        df = cargar_estructuras_proyectadas(ruta_estructuras)
        st.success("✅ Hoja 'estructuras' leída correctamente")
    except Exception as e:
        st.error(f"❌ No se pudo leer la hoja 'estructuras': {e}")
        st.stop()

    # Guardar en sesión
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

    try:
        # Procesar materiales usando la lógica del script principal
        df_resumen, df_estructuras_resumen, df_resumen_por_punto, datos_proyecto = procesar_materiales(
            ruta_estructuras, ruta_materiales
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

else:
    st.warning("⚠️ Debes subir ambos archivos: estructuras y base de datos de materiales.")

