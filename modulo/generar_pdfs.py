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

def generar_pdfs(modo_carga, archivo_estructuras, df, ruta_datos_materiales):
    # Procesar datos base
    df_resumen, df_estructuras_resumen, df_resumen_por_punto, datos_proyecto = procesar_materiales(
        archivo_estructuras=archivo_estructuras,
        archivo_materiales=ruta_datos_materiales,
        estructuras_df=df,
        datos_proyecto=st.session_state.get("datos_proyecto", {})
    )

    nombre_proyecto = datos_proyecto.get("nombre_proyecto", "Proyecto")

    # Generar PDFs individuales y completo
    pdfs = {
        "materiales": generar_pdf_materiales(df_resumen, nombre_proyecto, datos_proyecto),
        "estructuras_global": generar_pdf_estructuras_global(df_estructuras_resumen, nombre_proyecto),
        "estructuras_por_punto": generar_pdf_estructuras_por_punto(df_resumen_por_punto, nombre_proyecto),
        "materiales_por_punto": generar_pdf_materiales_por_punto(df_resumen_por_punto, nombre_proyecto),
        "completo": generar_pdf_completo(df_resumen, df_estructuras_resumen, df_resumen_por_punto, datos_proyecto),
    }

    return pdfs
