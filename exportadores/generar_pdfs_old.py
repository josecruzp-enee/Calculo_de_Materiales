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

# 🔥 IMPORTS NUEVOS (NO ROMPEN NADA)
from costos_precios.costos_estructuras import calcular_costos_por_estructura
from costos_precios.precio_por_estructura import calcular_precios_por_estructura


# =====================================================
# FORMATO TENSIÓN
# =====================================================
def formato_tension(v_ll):
    try:
        v_ll = float(v_ll)
        v_ln = round(v_ll / math.sqrt(3), 1)
        return f"{v_ln} L-N / {v_ll} L-L KV"
    except (ValueError, TypeError):
        return str(v_ll)


# =====================================================
# FUNCIÓN PRINCIPAL
# =====================================================
def generar_pdfs(modo_carga, archivo_estructuras, df, ruta_datos_materiales):

    # =====================================================
    # 1. PROCESAR
    # =====================================================
    df_resumen, df_estructuras_resumen, df_estructuras_por_punto, df_resumen_por_punto, datos_proyecto = procesar_materiales(
        archivo_estructuras=archivo_estructuras,
        archivo_materiales=ruta_datos_materiales,
        estructuras_df=df,
        datos_proyecto=st.session_state.get("datos_proyecto", {})
    )

    # =====================================================
    # 2. FORMATO TENSIÓN
    # =====================================================
    if "nivel_de_tension" in datos_proyecto and datos_proyecto["nivel_de_tension"]:
        datos_proyecto["nivel_de_tension"] = formato_tension(datos_proyecto["nivel_de_tension"])

    nombre_proyecto = datos_proyecto.get("nombre_proyecto", "Proyecto")

    # =====================================================
    # 3. MATERIALES EXTRA (SE DEJA IGUAL)
    # =====================================================
    adicionales = st.session_state.get("materiales_extra", [])

    if adicionales:
        df_adicionales = pd.DataFrame(adicionales)
        df_resumen = pd.concat([df_resumen, df_adicionales], ignore_index=True)
        df_resumen = df_resumen.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
        datos_proyecto["materiales_extra"] = df_adicionales
    else:
        datos_proyecto["materiales_extra"] = pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])

    # =====================================================
    # 🔥 4. INYECCIÓN DE PRECIOS (CLAVE)
    # =====================================================
    try:
        df_costos_estructura = calcular_costos_por_estructura(
            df_estructuras=df_estructuras_resumen,
            df_materiales_por_estructura=st.session_state.get("materiales_por_estructura", {}),
            df_precios_materiales=st.session_state.get("catalogo_costos", pd.DataFrame())
        )

        df_precios_estructura, _ = calcular_precios_por_estructura(
            df_costos_estructura,
            df_estructuras_resumen,
        )

        # 🔥 SOLO AGREGAMOS DATOS (NO CAMBIAMOS NADA)
        datos_proyecto["df_precios_estructura"] = df_precios_estructura
        datos_proyecto["total_proyecto"] = float(df_precios_estructura["Subtotal"].sum())

    except Exception as e:
        st.write("❌ ERROR CALCULANDO PRECIOS:", e)
        datos_proyecto["df_precios_estructura"] = pd.DataFrame()
        datos_proyecto["total_proyecto"] = 0

    # =====================================================
    # 5. GENERAR PDFs (TODO IGUAL)
    # =====================================================
    pdf_materiales = generar_pdf_materiales(df_resumen, nombre_proyecto, datos_proyecto)

    pdf_estructuras_global = generar_pdf_estructuras_global(
        df_estructuras_resumen,
        nombre_proyecto
    )

    pdf_estructuras_por_punto = generar_pdf_estructuras_por_punto(
        df_estructuras_por_punto,
        nombre_proyecto
    )

    pdf_materiales_por_punto = generar_pdf_materiales_por_punto(
        df_resumen_por_punto,
        nombre_proyecto
    )

    # 🔥 ESTE ES EL IMPORTANTE (YA RECIBE PRECIOS)
    pdf_informe_completo = generar_pdf_completo(
        df_resumen,
        df_estructuras_resumen,
        df_estructuras_por_punto,
        df_resumen_por_punto,
        datos_proyecto
    )

    # =====================================================
    # 6. OUTPUT
    # =====================================================
    pdfs = {
        "materiales": pdf_materiales,
        "estructuras_global": pdf_estructuras_global,
        "estructuras_por_punto": pdf_estructuras_por_punto,
        "materiales_por_punto": pdf_materiales_por_punto,
        "completo": pdf_informe_completo,
    }

    return pdfs
