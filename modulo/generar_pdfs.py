# modulo/pdf_descarga.py
import streamlit as st
from modulo.procesar_materiales import procesar_materiales
from modulo.pdf_utils import (
    generar_pdf_materiales,
    generar_pdf_estructuras_global,
    generar_pdf_estructuras_por_punto,
    generar_pdf_materiales_por_punto,
    generar_pdf_completo,
)

COLUMNAS_BASE = ["Punto", "Poste", "Primario", "Secundario", "Retenida", "Aterrizaje", "Transformador"]

def generar_pdfs(modo_carga, ruta_estructuras, df, ruta_datos_materiales="modulo/Estructura_datos.xlsx"):
    # Normalizar columnas mínimas
    for col in COLUMNAS_BASE:
        if col not in df.columns:
            df[col] = None

    archivo_estructuras = None if modo_carga in ["Pegar tabla", "Listas desplegables"] else ruta_estructuras

    df_resumen, df_estructuras_resumen, df_resumen_por_punto, datos_proyecto = procesar_materiales(
        archivo_estructuras=archivo_estructuras,
        archivo_materiales=ruta_datos_materiales,
        estructuras_df=df,
        datos_proyecto=st.session_state.get("datos_proyecto", {})
    )

    nombre_proyecto = datos_proyecto.get("nombre_proyecto", "Proyecto") if datos_proyecto else "Proyecto"

    st.download_button("📄 Descargar PDF de Materiales",
        generar_pdf_materiales(df_resumen, nombre_proyecto, datos_proyecto),
        "Resumen_Materiales.pdf", "application/pdf"
    )
    st.download_button("📄 Descargar PDF de Estructuras",
        generar_pdf_estructuras(df_estructuras_resumen, nombre_proyecto),
        "Resumen_Estructuras.pdf", "application/pdf"
    )
    st.download_button("📄 Descargar PDF Materiales por Punto",
        generar_pdf_materiales_por_punto(df_resumen_por_punto, nombre_proyecto),
        "Materiales_por_Punto.pdf", "application/pdf"
    )
    st.download_button("📄 Descargar Informe Completo (PDF)",
        generar_pdf_completo(df_resumen, df_estructuras_resumen, df_resumen_por_punto, datos_proyecto),
        "Informe_Completo.pdf", "application/pdf"
    )
