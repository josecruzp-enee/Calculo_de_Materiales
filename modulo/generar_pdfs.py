# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from modulo.procesar_materiales import procesar_materiales
from modulo.pdf_utils import (
    generar_pdf_materiales,
    generar_pdf_estructuras_global,
    generar_pdf_estructuras_por_punto,
    generar_pdf_materiales_por_punto,
    generar_pdf_completo
)

COLUMNAS_BASE = [
    "Punto", "Poste", "Primario", "Secundario",
    "Retenida", "Aterrizaje", "Transformador"
]

def generar_pdfs(modo_carga, archivo_estructuras, df, ruta_datos_materiales):
    """
    Genera los diferentes reportes PDF a partir de los datos del proyecto.
    Retorna un diccionario con los buffers PDF.
    """
    df_resumen, df_estructuras_resumen, df_resumen_por_punto, datos_proyecto = procesar_materiales(
        archivo_estructuras=archivo_estructuras,
        archivo_materiales=ruta_datos_materiales,
        estructuras_df=df,
        datos_proyecto=st.session_state.get("datos_proyecto", {})
    )

    nombre_proyecto = datos_proyecto.get("nombre_proyecto", "Proyecto")

    # ✅ Incorporar materiales adicionales si existen
    adicionales = st.session_state.get("materiales_extra", [])
    if adicionales:
        df_adicionales = pd.DataFrame(adicionales)
        # sumarlos al resumen general
        df_resumen = pd.concat([df_resumen, df_adicionales], ignore_index=True)
        df_resumen = df_resumen.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
    else:
        df_adicionales = pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])

    # ✅ Pasar los adicionales al PDF completo
    pdfs = {
        "materiales": generar_pdf_materiales(df_resumen, nombre_proyecto, datos_proyecto),
        "estructuras_global": generar_pdf_estructuras_global(df_estructuras_resumen, nombre_proyecto),
        "estructuras_por_punto": generar_pdf_estructuras_por_punto(df_resumen_por_punto, nombre_proyecto),
        "materiales_por_punto": generar_pdf_materiales_por_punto(df_resumen_por_punto, nombre_proyecto),
        "completo": generar_pdf_completo(
            df_resumen,
            df_estructuras_resumen,
            df_resumen_por_punto,
            datos_proyecto
        ),
    }

    return pdfs
