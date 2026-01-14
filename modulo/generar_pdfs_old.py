# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import math
from modulo.procesar_materiales import procesar_materiales
from modulo.pdf_utils import (
    generar_pdf_materiales,
    generar_pdf_estructuras_global,
    generar_pdf_estructuras_por_punto,
    generar_pdf_materiales_por_punto,
    generar_pdf_completo
)

# === Función auxiliar para formatear el nivel de tensión ===
def formato_tension(v_ll):
    """Convierte 13.8 -> '7.9 L-N / 13.8 L-L KV'"""
    try:
        v_ll = float(v_ll)
        v_ln = round(v_ll / math.sqrt(3), 1)
        return f"{v_ln} L-N / {v_ll} L-L KV"
    except (ValueError, TypeError):
        return str(v_ll)


def generar_pdfs(modo_carga, archivo_estructuras, df, ruta_datos_materiales):
    """
    Genera todos los reportes PDF del proyecto:
    - Resumen de materiales
    - Estructuras globales
    - Estructuras por punto
    - Materiales por punto
    - Informe completo consolidado
    """

    # === 1️⃣ Procesar materiales y estructuras ===
    df_resumen, df_estructuras_resumen, df_estructuras_por_punto, df_resumen_por_punto, datos_proyecto = procesar_materiales(
        archivo_estructuras=archivo_estructuras,
        archivo_materiales=ruta_datos_materiales,
        estructuras_df=df,
        datos_proyecto=st.session_state.get("datos_proyecto", {})
    )

    # === 2️⃣ Formatear tensión en texto legible ===
    if "nivel_de_tension" in datos_proyecto and datos_proyecto["nivel_de_tension"]:
        datos_proyecto["nivel_de_tension"] = formato_tension(datos_proyecto["nivel_de_tension"])

    nombre_proyecto = datos_proyecto.get("nombre_proyecto", "Proyecto")

    # === 3️⃣ Materiales adicionales (si existen) ===
    adicionales = st.session_state.get("materiales_extra", [])
    if adicionales:
        df_adicionales = pd.DataFrame(adicionales)
        df_resumen = pd.concat([df_resumen, df_adicionales], ignore_index=True)
        df_resumen = df_resumen.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
        datos_proyecto["materiales_extra"] = df_adicionales
    else:
        datos_proyecto["materiales_extra"] = pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])

    # === 4️⃣ Generar cada PDF ===
    pdf_materiales = generar_pdf_materiales(df_resumen, nombre_proyecto, datos_proyecto)
    pdf_estructuras_global = generar_pdf_estructuras_global(df_estructuras_resumen, nombre_proyecto)
    pdf_estructuras_por_punto = generar_pdf_estructuras_por_punto(df_estructuras_por_punto, nombre_proyecto)
    pdf_materiales_por_punto = generar_pdf_materiales_por_punto(df_resumen_por_punto, nombre_proyecto)
    pdf_informe_completo = generar_pdf_completo(
        df_resumen,
        df_estructuras_resumen,
        df_estructuras_por_punto,
        df_resumen_por_punto,
        datos_proyecto
    )

    # === 5️⃣ Devolver todo como diccionario ===
    pdfs = {
        "materiales": pdf_materiales,
        "estructuras_global": pdf_estructuras_global,
        "estructuras_por_punto": pdf_estructuras_por_punto,
        "materiales_por_punto": pdf_materiales_por_punto,
        "completo": pdf_informe_completo,
    }

    return pdfs
