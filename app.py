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


# Columnas base para DataFrame
COLUMNAS = ["Punto", "Poste", "Primario", "Secundario", "Retenida", "Aterrizaje", "Transformador"]

# Archivo de materiales ya dentro del proyecto
RUTA_MATERIALES = os.path.join("modulo", "Estructura_datos.xlsx")


def mostrar_info_proyecto(datos_proyecto):
    st.subheader("📑 Información del Proyecto")
    st.markdown(f"**Nombre del Proyecto:** {datos_proyecto.get('nombre_proyecto', '')}")
    st.markdown(f"**Código / Expediente:** {datos_proyecto.get('codigo_proyecto', '')}")
    st.markdown(f"**Nivel de Tensión (kV):** {datos_proyecto.get('nivel_de_tension', '')}")
    st.markdown(f"**Calibre del Conductor de Media Tensión:** {datos_proyecto.get('calibre_primario', '')}")
    st.markdown(f"**Calibre del Conductor Secundario:** {datos_proyecto.get('calibre_secundario', '')}")
    st.markdown(f"**Calibre del Neutro:** {datos_proyecto.get('calibre_neutro', '')}")
    st.markdown(f"**Calibre del Piloto:** {datos_proyecto.get('calibre_piloto', '')}")
    st.markdown(f"**Calibre del Cable de Retenidas:** {datos_proyecto.get('calibre_retenidas', '')}")
    st.markdown(f"**Responsable / Diseñador:** {datos_proyecto.get('responsable', 'N/A')}")
    st.markdown(f"**Empresa / Área:** {datos_proyecto.get('empresa', 'N/A')}")


def guardar_archivo_temporal(archivo_subido):
    temp_dir = tempfile.mkdtemp()
    ruta_temporal = os.path.join(temp_dir, archivo_subido.name)
    with open(ruta_temporal, "wb") as f:
        f.write(archivo_subido.getbuffer())
    return ruta_temporal


def exportar_tabla(df):
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


def mostrar_exportar_pdfs(df_resumen, df_estructuras_resumen, df_resumen_por_punto, datos_proyecto):
    st.subheader("📑 Exportar a PDF")

    try:
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


def main():
    st.set_page_config(page_title="Cálculo de Materiales", layout="wide")
    st.title("⚡ Cálculo de Materiales para Proyecto de Distribución")

    st.subheader("📂 Sube el archivo de estructuras")
    archivo_estructuras = st.file_uploader("📌 Archivo de estructuras (estructuras_lista.xlsx)", type=["xlsx"])

    if archivo_estructuras:
        ruta_estructuras = guardar_archivo_temporal(archivo_estructuras)

        # === Leer datos del proyecto ===
        try:
            datos_proyecto = cargar_datos_proyecto(ruta_estructuras)
            mostrar_info_proyecto(datos_proyecto)
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

        # Guardar en sesión para mantener el estado
        st.session_state["df_puntos"] = df.copy()

        # ================== EDITOR DE TABLA ==================
        df = st.data_editor(
            st.session_state.get("df_puntos", pd.DataFrame(columns=COLUMNAS)),
            num_rows="dynamic",
            use_container_width=True,
        )
        st.session_state["df_puntos"] = df

        # Vista previa
        st.subheader("📑 Vista previa de la tabla")
        st.dataframe(df, use_container_width=True)

        # ================== EXPORTAR TABLA ==================
        st.subheader("📥 Exportar tabla")
        exportar_tabla(df)

        # ================== GENERAR PDFs ==================
        try:
            df_resumen, df_estructuras_resumen, df_resumen_por_punto, datos_proyecto = procesar_materiales(
                ruta_estructuras, RUTA_MATERIALES
            )
            mostrar_exportar_pdfs(df_resumen, df_estructuras_resumen, df_resumen_por_punto, datos_proyecto)
        except Exception as e:
            st.error(f"⚠️ Error al procesar materiales: {e}")

    else:
        st.warning("⚠️ Debes subir el archivo de estructuras.")


if __name__ == "__main__":
    main()
