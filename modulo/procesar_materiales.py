# -*- coding: utf-8 -*-
"""
procesar_materiales.py
Versión modularizada para Streamlit y consola
"""

import pandas as pd
from collections import Counter

# === Debug ===
try:
    import streamlit as st
    log = st.write
except ImportError:
    log = print

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
    aplicar_reemplazos_conectores
)

# =====================================================
# Funciones auxiliares
# =====================================================

def limpiar_codigo(codigo):
    if pd.isna(codigo) or str(codigo).strip() == "":
        return None, None
    codigo = str(codigo).strip()

    # 👉 Si es solo un número, es un punto, no una estructura
    if codigo.isdigit():
        return None, "PUNTO"

    # Normalización de nombres con paréntesis
    if codigo.endswith(")") and "(" in codigo:
        base = codigo[:codigo.rfind("(")].strip()
        tipo = codigo[codigo.rfind("(")+1:codigo.rfind(")")].strip().upper()
        return base, tipo

    return codigo, "P"


def expandir_lista_codigos(cadena):
    if not cadena:
        return []
    return [parte.strip() for parte in str(cadena).split(",") if parte.strip()]


def validar_datos_proyecto(datos_proyecto):
    """Verifica que al menos tensión y calibre MT estén definidos."""
    tension = str(datos_proyecto.get("nivel_de_tension", "")).strip()
    calibre_mt = datos_proyecto.get("calibre_primario", "")
    if not tension or not calibre_mt:
        log("⚠️ No se han definido tensión o calibre de MT. Esperando datos...")
        return None, None
    return tension, calibre_mt


def extraer_conteo_estructuras(df_estructuras):
    """Limpia códigos y devuelve un Counter de estructuras."""
    estructuras_proyectadas, estructuras_por_punto = extraer_estructuras_proyectadas(df_estructuras)
    log(f"📊 estructuras_proyectadas: {estructuras_proyectadas}")
    log(f"📊 estructuras_por_punto: {estructuras_por_punto}")

    estructuras_limpias = []
    for e in estructuras_proyectadas:
        for parte in expandir_lista_codigos(e):
            codigo, tipo = limpiar_codigo(parte)
            if codigo:
                estructuras_limpias.append(codigo)
    conteo = Counter(estructuras_limpias)
    log(f"📊 Conteo de estructuras limpias: {conteo}")
    return conteo, estructuras_por_punto


def calcular_materiales_estructura(archivo_materiales, estructura, cant, tension, calibre_mt, tabla_conectores_mt):
    """Procesa materiales para una estructura específica."""
    try:
        log(f"🔍 Cargando hoja '{estructura}' (cantidad={cant})")
        df_temp = cargar_materiales(archivo_materiales, estructura, header=None)
        log(f"   ❇️ Primeras 3 filas de '{estructura}':\n{df_temp.head(3)}")

        # Detectar fila del encabezado
        fila_tension = next(
            i for i, row in df_temp.iterrows()
            if any(str(tension) in str(cell) for cell in row)
        )
        df = cargar_materiales(archivo_materiales, estructura, header=fila_tension)

        df.columns = df.columns.map(str).str.strip()
        if "Materiales" not in df.columns or str(tension) not in df.columns:
            log(f"⚠️ Hoja '{estructura}' no tiene columna 'Materiales' o '{tension}'")
            return pd.DataFrame()

        # Filtrar materiales
        df_filtrado = df[df[str(tension)] > 0][["Materiales", "Unidad", str(tension)]].copy()
        df_filtrado["Materiales"] = aplicar_reemplazos_conectores(
            df_filtrado["Materiales"].tolist(),
            calibre_mt,
            tabla_conectores_mt
        )
        df_filtrado["Cantidad"] = df_filtrado[str(tension)] * cant

        log(f"   ✅ Materiales agregados para '{estructura}': {len(df_filtrado)} filas")
        return df_filtrado[["Materiales", "Unidad", "Cantidad"]]

    except Exception as e:
        log(f"❌ Error al procesar hoja '{estructura}': {e}")
        return pd.DataFrame()


def calcular_materiales_por_punto(archivo_materiales, estructuras_por_punto, tension):
    """Procesa materiales agrupados por punto."""
    resumen_punto = []
    for punto, estructuras in estructuras_por_punto.items():
        log(f"📌 Procesando punto '{punto}' con estructuras: {estructuras}")
        for est in estructuras:
            for parte in expandir_lista_codigos(est):
                codigo, tipo = limpiar_codigo(parte)
                if not codigo:
                    continue
                try:
                    df_temp = cargar_materiales(archivo_materiales, codigo, header=None)
                    fila_tension = next(
                        i for i, row in df_temp.iterrows()
                        if any(str(tension) in str(cell) for cell in row)
                    )
                    df = cargar_materiales(archivo_materiales, codigo, header=fila_tension)
                    df.columns = df.columns.map(str).str.strip()
                    if "Materiales" not in df.columns or str(tension) not in df.columns:
                        continue

                    dfp = df[df[str(tension)] > 0][["Materiales", "Unidad", str(tension)]].copy()
                    dfp["Cantidad"] = dfp[str(tension)]
                    dfp["Punto"] = punto
                    resumen_punto.append(dfp[["Punto", "Materiales", "Unidad", "Cantidad"]])

                    log(f"   ✅ Materiales por punto agregados para '{codigo}': {len(dfp)} filas")
                except Exception as e:
                    log(f"❌ Error al procesar hoja '{codigo}' en punto '{punto}': {e}")
    return (
        pd.concat(resumen_punto, ignore_index=True)
          .groupby(["Punto","Materiales","Unidad"], as_index=False)["Cantidad"].sum()
        if resumen_punto else
        pd.DataFrame(columns=["Punto","Materiales","Unidad","Cantidad"])
    )

# =====================================================
# Función principal
# =====================================================

def procesar_materiales(archivo_estructuras=None, archivo_materiales=None, estructuras_df=None, datos_proyecto=None):
    """Función principal que orquesta el cálculo de materiales."""
    # --- Cargar datos y estructuras ---
    if archivo_estructuras:
        datos_proyecto = cargar_datos_proyecto(archivo_estructuras)
        df_estructuras = cargar_estructuras_proyectadas(archivo_estructuras)
    elif estructuras_df is not None:
        datos_proyecto = datos_proyecto or {}
        df_estructuras = estructuras_df.copy()
    else:
        raise ValueError("Debe proporcionar archivo_estructuras o estructuras_df")

    # --- Merge de datos del proyecto ---
    if "datos_proyecto" in st.session_state:
        datos_proyecto = {**st.session_state["datos_proyecto"], **datos_proyecto}
    log("📌 Datos del proyecto:", datos_proyecto)

    # --- Validar proyecto ---
    tension, calibre_mt = validar_datos_proyecto(datos_proyecto)
    if not tension or not calibre_mt:
        return (
            pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"]),
            pd.DataFrame(columns=["NombreEstructura", "Cantidad"]),
            pd.DataFrame(columns=["Punto", "Materiales", "Unidad", "Cantidad"]),
            datos_proyecto
        )

    # --- Estructuras y conteo ---
    conteo, estructuras_por_punto = extraer_conteo_estructuras(df_estructuras)

    # --- Índice y conectores ---
    df_indice = cargar_indice(archivo_materiales)
    tabla_conectores_mt = cargar_conectores_mt(archivo_materiales)

    # --- Calcular materiales por estructura ---
    df_total = pd.concat(
        [calcular_materiales_estructura(archivo_materiales, e, c, tension, calibre_mt, tabla_conectores_mt)
         for e, c in conteo.items()],
        ignore_index=True
    )

    # --- Materiales adicionales ---
    if archivo_estructuras:
        df_adicionales = cargar_adicionales(archivo_estructuras)
        df_total = pd.concat([df_total, df_adicionales], ignore_index=True)

    # --- Resumen general ---
    df_resumen = df_total.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum() if not df_total.empty else pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])
    df_indice["Cantidad"] = df_indice["NombreEstructura"].map(conteo).fillna(0).astype(int)
    df_estructuras_resumen = df_indice[df_indice["Cantidad"] > 0]

    # --- Resumen por punto ---
    df_resumen_por_punto = calcular_materiales_por_punto(archivo_materiales, estructuras_por_punto, tension)

    log(f"📊 Resumen final: {len(df_resumen)} materiales, {len(df_estructuras_resumen)} estructuras, {len(df_resumen_por_punto)} filas por punto")

    return df_resumen, df_estructuras_resumen, df_resumen_por_punto, datos_proyecto

