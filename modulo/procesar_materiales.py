# -*- coding: utf-8 -*-
"""
procesar_materiales_debug.py
Versión con debug completo para Streamlit y consola
"""

import os
import pandas as pd
from collections import Counter

# === Para mostrar debug en Streamlit si está disponible ===
try:
    import streamlit as st
    log = st.write
except ImportError:
    log = print

# 🔒 Fallback absoluto: si otro módulo llama sin log definido
try:
    log
except NameError:
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
from modulo.conectores_mt import cargar_conectores_mt, aplicar_reemplazos_conectores


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


def procesar_materiales(archivo_estructuras=None, archivo_materiales=None, estructuras_df=None):
    # --- Datos de proyecto ---
    if archivo_estructuras:
        datos_proyecto = cargar_datos_proyecto(archivo_estructuras)
        df_estructuras = cargar_estructuras_proyectadas(archivo_estructuras)
        log(f"✅ Cargado archivo_estructuras: {archivo_estructuras}")
    elif estructuras_df is not None:
        datos_proyecto = {}
        df_estructuras = estructuras_df.copy()
        log("✅ Usando estructuras_df directamente")
    else:
        raise ValueError("Debe proporcionar archivo_estructuras o estructuras_df")

    log("📌 Datos del proyecto:", datos_proyecto)

    nombre_proyecto = datos_proyecto.get("nombre_proyecto", "Proyecto")
    tension = st.selectbox("Selecciona tensión:", ["", "13.8", "34.5"])

# Construir el diccionario de proyecto
    datos_proyecto = {
        "nombre_proyecto": "Proyecto",
        "nivel_de_tension": tension,
        "calibre_primario": calibre,
    }

    # --- Validar que se definieron tensión y calibre ---
    if not tension or not calibre_primario:
        log("⚠️ No se han definido tensión o calibre del conductor. Esperando datos...")
        return (
            pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"]),
            pd.DataFrame(columns=["NombreEstructura", "Cantidad"]),
            pd.DataFrame(columns=["Punto", "Materiales", "Unidad", "Cantidad"]),
            datos_proyecto
        )

    # --- Extraer estructuras ---
    estructuras_proyectadas, estructuras_por_punto = extraer_estructuras_proyectadas(df_estructuras)
    log(f"📊 estructuras_proyectadas: {estructuras_proyectadas}")
    log(f"📊 estructuras_por_punto: {estructuras_por_punto}")

    # --- Limpiar códigos ---
    estructuras_limpias = []
    for e in estructuras_proyectadas:
        for parte in expandir_lista_codigos(e):
            codigo, tipo = limpiar_codigo(parte)
            if codigo:
                estructuras_limpias.append(codigo)
    conteo = Counter(estructuras_limpias)
    log(f"📊 Conteo de estructuras limpias: {conteo}")

    # --- Índice y conectores ---
    df_indice = cargar_indice(archivo_materiales)
    tabla_conectores_mt = cargar_conectores_mt(archivo_materiales)
    log(f"📌 Hojas de índice cargadas: {df_indice.shape[0]} filas")
    log(f"📌 Conectores cargados: {tabla_conectores_mt.shape[0]} filas")

    # --- Calculo de materiales ---
    df_total = pd.DataFrame()
    for estructura, cant in conteo.items():
        try:
            log(f"🔍 Cargando hoja '{estructura}' (cantidad={cant})")
            df_temp = cargar_materiales(archivo_materiales, estructura, header=None)
            log(f"   ❇️ Primeras 3 filas de '{estructura}':\n{df_temp.head(3)}")

            # Detectar fila del encabezado
            fila_tension = next(i for i, row in df_temp.iterrows() if any(str(tension) in str(cell) for cell in row))
            df = cargar_materiales(archivo_materiales, estructura, header=fila_tension)

            df.columns = df.columns.map(str).str.strip()
            if "Materiales" not in df.columns or str(tension) not in df.columns:
                log(f"⚠️ Hoja '{estructura}' no tiene columna 'Materiales' o '{tension}'")
                continue

            # --- Filtrar y preparar materiales ---
            df_filtrado = df[df[str(tension)] > 0][["Materiales", "Unidad", str(tension)]].copy()

            log(f"   📝 Materiales brutos de '{estructura}' con tensión={tension}:")
            for _, fila in df_filtrado.iterrows():
                log(f"      - {fila['Materiales']} | {fila['Unidad']} | {fila[str(tension)]}")

            df_filtrado["Materiales"] = aplicar_reemplazos_conectores(
                df_filtrado["Materiales"].tolist(),
                calibre_primario,
                tabla_conectores_mt
            )
            df_filtrado["Cantidad"] = df_filtrado[str(tension)] * cant

            df_total = pd.concat([df_total, df_filtrado[["Materiales", "Unidad", "Cantidad"]]])
            log(f"   ✅ Materiales agregados para '{estructura}': {len(df_filtrado)} filas")
        except Exception as e:
            log(f"❌ Error al procesar hoja '{estructura}': {e}")

    # --- Materiales adicionales ---
    if archivo_estructuras:
        df_adicionales = cargar_adicionales(archivo_estructuras)
        df_total = pd.concat([df_total, df_adicionales[["Materiales", "Unidad", "Cantidad"]]])
        log(f"📌 Materiales adicionales agregados: {df_adicionales.shape[0]} filas")

    # --- Resumen general ---
    df_resumen = (
        df_total.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
        if not df_total.empty
        else pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])
    )
    df_indice["Cantidad"] = df_indice["NombreEstructura"].map(conteo).fillna(0).astype(int)
    df_estructuras_resumen = df_indice[df_indice["Cantidad"] > 0]

    # --- Resumen por punto ---
    resumen_punto = []
    for punto, estructuras in estructuras_por_punto.items():
        log(f"📌 Procesando punto '{punto}' con estructuras: {estructuras}")
        for est in estructuras:
            for parte in expandir_lista_codigos(est):
                codigo, tipo = limpiar_codigo(parte)
                if codigo:
                    try:
                        df_temp = cargar_materiales(archivo_materiales, codigo, header=None)
                        fila_tension = next(i for i, row in df_temp.iterrows() if any(str(tension) in str(cell) for cell in row))
                        df = cargar_materiales(archivo_materiales, codigo, header=fila_tension)

                        df.columns = df.columns.map(str).str.strip()
                        if "Materiales" not in df.columns or str(tension) not in df.columns:
                            continue

                        dfp = df[df[str(tension)] > 0][["Materiales", "Unidad", str(tension)]].copy()

                        log(f"   📝 Materiales brutos de '{codigo}' en punto '{punto}':")
                        for _, fila in dfp.iterrows():
                            log(f"      - {fila['Materiales']} | {fila['Unidad']} | {fila[str(tension)]}")

                        dfp["Cantidad"] = dfp[str(tension)]
                        dfp["Punto"] = punto
                        resumen_punto.append(dfp[["Punto", "Materiales", "Unidad", "Cantidad"]])
                        log(f"   ✅ Materiales por punto agregados para '{codigo}': {len(dfp)} filas")
                    except Exception as e:
                        log(f"❌ Error al procesar hoja '{codigo}' en punto '{punto}': {e}")

    df_resumen_por_punto = (
        pd.concat(resumen_punto, ignore_index=True)
          .groupby(["Punto","Materiales","Unidad"], as_index=False)["Cantidad"].sum()
        if resumen_punto else
        pd.DataFrame(columns=["Punto","Materiales","Unidad","Cantidad"])
    )

    log(f"📊 Resumen final: {df_resumen.shape[0]} materiales, {df_estructuras_resumen.shape[0]} estructuras, {df_resumen_por_punto.shape[0]} filas por punto")

    return df_resumen, df_estructuras_resumen, df_resumen_por_punto, datos_proyecto

