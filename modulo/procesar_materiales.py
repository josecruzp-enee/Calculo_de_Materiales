# -*- coding: utf-8 -*-
"""
procesar_materiales.py
Versión con mensajes de depuración visibles en Streamlit
"""

import os
import sys
import pandas as pd
from collections import Counter

# === Para mostrar debug en Streamlit si está disponible ===
try:
    import streamlit as st
    log = st.write
except ImportError:
    log = print  # fallback a consola si no hay Streamlit

# === Módulos propios ===
from modulo.entradas import (
    cargar_datos_proyecto,
    cargar_estructuras_proyectadas,
    extraer_estructuras_proyectadas,
    cargar_indice,
    cargar_adicionales,
    cargar_materiales,
)
from modulo.conectores_mt import (
    cargar_conectores_mt,
    aplicar_reemplazos_conectores,
)
from modulo.pdf_utils import (
    generar_pdf_materiales,
    generar_pdf_estructuras,
    generar_pdf_materiales_por_punto,
    generar_pdf_completo,
)
from modulo.excel_utils import exportar_excel


# =====================================================
# Funciones auxiliares
# =====================================================

def limpiar_codigo(codigo):
    if pd.isna(codigo) or str(codigo).strip() == "":
        return None, None

    codigo = str(codigo).strip()

    if "–" in codigo:
        codigo = codigo.split("–")[0].strip()
    elif " - " in codigo:
        codigo = codigo.split(" - ")[0].strip()

    if codigo.endswith(")") and "(" in codigo:
        base = codigo[:codigo.rfind("(")].strip()
        tipo = codigo[codigo.rfind("(") + 1 : codigo.rfind(")")].strip().upper()
        return base, tipo

    return codigo, "P"


def expandir_lista_codigos(cadena):
    if not cadena:
        return []
    return [parte.strip() for parte in str(cadena).split(",") if parte.strip()]


# =====================================================
# Procesamiento principal
# =====================================================

def procesar_materiales(archivo_estructuras=None, archivo_materiales=None, estructuras_df=None):
    if archivo_estructuras is not None:
        datos_proyecto = cargar_datos_proyecto(archivo_estructuras)
        df_estructuras = cargar_estructuras_proyectadas(archivo_estructuras)
    elif estructuras_df is not None:
        datos_proyecto = {}
        df_estructuras = estructuras_df.copy()
    else:
        raise ValueError("Debe proporcionar archivo_estructuras o estructuras_df")

    nombre_proyecto = datos_proyecto.get("nombre_proyecto", "Proyecto")
    tension = datos_proyecto.get("nivel_de_tension") or datos_proyecto.get("tension")
    calibre_primario = datos_proyecto.get("calibre_primario", "1/0 ASCR")

    if tension:
        tension = str(tension).replace(",", ".").replace("kV", "").strip()

    estructuras_proyectadas, estructuras_por_punto = extraer_estructuras_proyectadas(df_estructuras)

    estructuras_limpias = []
    for e in estructuras_proyectadas:
        for parte in expandir_lista_codigos(e):
            codigo, tipo = limpiar_codigo(parte)
            if codigo and (tipo == "P" or not tipo):
                estructuras_limpias.append(codigo)

    conteo = Counter(estructuras_limpias)

    log(f"📊 Conteo de estructuras proyectadas: {conteo}")

    df_indice = cargar_indice(archivo_materiales)
    tabla_conectores_mt = cargar_conectores_mt(archivo_materiales)

    df_total = pd.DataFrame()
    for estructura, cant in conteo.items():
        try:
            log(f"🔍 Intentando cargar estructura '{estructura}' (cantidad={cant})")
            df_temp = cargar_materiales(archivo_materiales, estructura, header=None)
            fila_tension = next(
                i for i, row in df_temp.iterrows() if any(str(tension) in str(cell) for cell in row)
            )
            df = cargar_materiales(archivo_materiales, estructura, header=fila_tension)

            df.columns = df.columns.map(lambda x: str(x).strip())
            if "Materiales" not in df.columns or tension not in df.columns:
                log(f"⚠️ Estructura {estructura} no tiene columna 'Materiales' o '{tension}'")
                continue

            unidad_col = df.columns[df.columns.get_loc("Materiales") + 1]
            df_filtrado = df[df[tension] > 0][["Materiales", unidad_col, tension]].copy()

            df_filtrado["Materiales"] = aplicar_reemplazos_conectores(
                df_filtrado["Materiales"].tolist(), calibre_primario, tabla_conectores_mt
            )
            df_filtrado["Unidad"] = df_filtrado[unidad_col]
            df_filtrado["Cantidad"] = df_filtrado[tension] * cant
            df_total = pd.concat([df_total, df_filtrado[["Materiales", "Unidad", "Cantidad"]]])
        except Exception as e:
            log(f"❌ Error en estructura {estructura}: {e}")

    if archivo_estructuras is not None:
        df_adicionales = cargar_adicionales(archivo_estructuras)
        df_total = pd.concat([df_total, df_adicionales[["Materiales", "Unidad", "Cantidad"]]])

    df_resumen = (
        df_total.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
        if not df_total.empty
        else pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])
    )
    df_indice["Cantidad"] = df_indice["NombreEstructura"].map(conteo).fillna(0).astype(int)
    df_estructuras_resumen = df_indice[df_indice["Cantidad"] > 0]

    resumen_punto = []
    for punto, estructuras in estructuras_por_punto.items():
        log(f"📌 Procesando punto {punto} con estructuras {estructuras}")
        for est in estructuras:
            for parte in expandir_lista_codigos(est):
                codigo, tipo = limpiar_codigo(parte)
                if codigo and (tipo == "P" or not tipo):
                    try:
                        df_temp = cargar_materiales(archivo_materiales, codigo, header=None)
                        fila_tension = next(
                            i for i, row in df_temp.iterrows() if any(str(tension) in str(cell) for cell in row)
                        )
                        df = cargar_materiales(archivo_materiales, codigo, header=fila_tension)

                        df.columns = df.columns.map(lambda x: str(x).strip())
                        unidad_col = df.columns[df.columns.get_loc("Materiales") + 1]
                        dfp = df[df[tension] > 0][["Materiales", unidad_col, tension]].copy()
                        dfp["Unidad"] = dfp[unidad_col]
                        dfp["Cantidad"] = dfp[tension]
                        dfp["Punto"] = punto
                        resumen_punto.append(dfp[["Punto", "Materiales", "Unidad", "Cantidad"]])
                    except Exception as e:
                        log(f"❌ Error en estructura {codigo}: {e}")

    df_resumen_por_punto = (
        pd.concat(resumen_punto, ignore_index=True)
        .groupby(["Punto", "Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
        if resumen_punto else pd.DataFrame(columns=["Punto", "Materiales", "Unidad", "Cantidad"])
    )

    return df_resumen, df_estructuras_resumen, df_resumen_por_punto, datos_proyecto
