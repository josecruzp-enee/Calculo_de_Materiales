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
    """
    Convierte el valor de tensión de línea a línea (kV) en un texto del tipo:
    '19.9 L-N / 34.5 L-L kV'
    """
    try:
        v_ll = float(v_ll)
        v_ln = round(v_ll / math.sqrt(3), 1)
        return f"{v_ln} L-N / {v_ll} L-L kV"
    except (ValueError, TypeError):
        # Si el dato no es numérico, lo devuelve tal cual
        return str(v_ll)


def generar_pdfs(modo_carga, archivo_estructuras, df, ruta_datos_materiales):
    """
    Genera todos los reportes PDF del proyecto:
    - Lista de materiales global
    - Materiales adicionados
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

    # --- Aplicar formato especial al nivel de tensión ---
    if "nivel_de_tension" in datos_proyecto and datos_proyecto["nivel_de_tension"]:
        datos_proyecto["nivel_de_tension"] = formato_tension(datos_proyecto["nivel_de_tension"])

    nombre_proyecto = datos_proyecto.get("nombre_proyecto", "Proyecto")

    # === 🧪 DEPURACIÓN: mostrar qué llega ===
    st.write("🧪 df_resumen (materiales):", df_resumen.head())
    st.write("🧪 df_estructuras_resumen:", df_estructuras_resumen.head())
    st.write("🧪 df_estructuras_por_punto:", df_estructuras_por_punto.head())
    st.write("🧪 df_resumen_por_punto (materiales por punto):", df_resumen_por_punto.head())
    st.write("🧪 datos_proyecto:", datos_proyecto)

    # === 2️⃣ Incorporar materiales adicionales (si existen) ===
    adicionales = st.session_state.get("materiales_extra", [])
    if adicionales:
        df_adicionales = pd.DataFrame(adicionales)
        # Combinar con el resumen global
        df_resumen = pd.concat([df_resumen, df_adicionales], ignore_index=True)
        df_resumen = df_resumen.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
        # Guardar también dentro de datos_proyecto para incluir en PDF completo
        datos_proyecto["materiales_extra"] = df_adicionales
    else:
        df_adicionales = pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])
        datos_proyecto["materiales_extra"] = df_adicionales

    # === 3️⃣ Generar los diferentes PDF ===
    pdfs = {
        "materiales": generar_pdf_materiales(df_resumen, nombre_proyecto, datos_proyecto),
        "estructuras_global": generar_pdf_estructuras_global(df_estructuras_resumen, nombre_proyecto),
        "estructuras_por_punto": generar_pdf_estructuras_por_punto(df_estructuras_por_punto, nombre_proyecto),
        "materiales_por_punto": generar_pdf_materiales_por_punto(df_resumen_por_punto, nombre_proyecto),
        "completo": generar_pdf_completo(
            df_resumen,
            df_estructuras_resumen,
            df_estructuras_por_punto,
            df_resumen_por_punto,
            datos_proyecto
        ),
    }

    return pdfs
