# -*- coding: utf-8 -*-
"""
procesar_materiales_debug.py - VERSIÓN CORREGIDA
Busca específicamente columnas "34.5" y "13.8"
"""

import os
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
        if isinstance(estructuras_df, tuple) and len(estructuras_df) == 2:
            df_estructuras, datos_proyecto = estructuras_df
        else:
            df_estructuras = estructuras_df.copy()
            datos_proyecto = {
                "nombre_proyecto": "Proyecto",
                "nivel_de_tension": "13.8",
                "calibre_primario": "1/0 ASCR"
            }
        log("✅ Usando estructuras_df directamente")
    else:
        raise ValueError("Debe proporcionar archivo_estructuras o estructuras_df")

    log("📌 Datos del proyecto:")
    log(datos_proyecto)

    nombre_proyecto = datos_proyecto.get("nombre_proyecto", "Proyecto")
    tension_proyecto = str(datos_proyecto.get("nivel_de_tension") or datos_proyecto.get("tension", "13.8"))\
        .replace(",", ".").replace("kV", "").strip()
    calibre_primario = datos_proyecto.get("calibre_primario", "1/0 ASCR")

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

    # --- CÁLCULO DE MATERIALES - VERSIÓN CORREGIDA ---
    df_total = pd.DataFrame()
    
    for estructura, cant in conteo.items():
        try:
            log(f"🔍 Cargando hoja '{estructura}' (cantidad={cant})")
            
            # Intentar cargar la hoja
            df_temp = cargar_materiales(archivo_materiales, estructura, header=None)
            if df_temp.empty:
                log(f"❌ Hoja '{estructura}' está vacía o no existe")
                continue
                
            log(f"❇️ Primeras 3 filas de '{estructura}':")
            log(df_temp.head(3))

            # BUSCAR FILA QUE CONTIENE LAS COLUMNAS "34.5" Y "13.8"
            fila_encabezado = None
            for i, row in df_temp.iterrows():
                # Verificar si esta fila contiene "34.5" y "13.8"
                tiene_34_5 = any("34.5" in str(cell) for cell in row)
                tiene_13_8 = any("13.8" in str(cell) for cell in row)
                
                if tiene_34_5 and tiene_13_8:
                    fila_encabezado = i
                    log(f"✅ Encontrado encabezado en fila {i} con columnas '34.5' y '13.8'")
                    break
            
            if fila_encabezado is None:
                log(f"⚠️ No se encontró encabezado con columnas '34.5' y '13.8' en hoja '{estructura}'")
                # Mostrar qué contenía cada fila para debug
                for i, row in df_temp.iterrows():
                    log(f"   Fila {i}: {list(row)}")
                continue

            # Cargar con el header correcto
            df = cargar_materiales(archivo_materiales, estructura, header=fila_encabezado)
            
            # --- NORMALIZACIÓN DE COLUMNAS - MANTENER "34.5" y "13.8" ---
            df.columns = df.columns.astype(str).str.strip()
            
            log(f"🔍 Columnas originales en '{estructura}': {list(df.columns)}")
            
            # Verificar que tenemos las columnas necesarias
            columnas_necesarias = ["34.5", "13.8", "MATERIALES", "UNIDAD"]
            columnas_encontradas = []
            
            for col in df.columns:
                if "34.5" in col:
                    columnas_encontradas.append("34.5")
                elif "13.8" in col:
                    columnas_encontradas.append("13.8")
                elif "MATERIAL" in col.upper():
                    columnas_encontradas.append("MATERIALES")
                elif "UNIDAD" in col.upper() or "UND" in col.upper():
                    columnas_encontradas.append("UNIDAD")
                elif "COD" in col.upper():
                    columnas_encontradas.append("COD_ENEE")
            
            log(f"✅ Columnas detectadas: {columnas_encontradas}")

            # Verificar que tenemos las columnas de tensión
            if "34.5" not in df.columns or "13.8" not in df.columns:
                log(f"❌ Hoja '{estructura}' no tiene columnas '34.5' y '13.8'")
                log(f"   Columnas disponibles: {list(df.columns)}")
                continue

            if "MATERIALES" not in df.columns:
                log(f"❌ Hoja '{estructura}' no tiene columna 'MATERIALES'")
                continue

            # --- FILTRAR MATERIALES SEGÚN TENSIÓN DEL PROYECTO ---
            try:
                # Determinar qué columna usar según la tensión del proyecto
                if tension_proyecto == "34.5":
                    columna_tension = "34.5"
                    columna_opuesta = "13.8"
                else:  # 13.8 por defecto
                    columna_tension = "13.8" 
                    columna_opuesta = "34.5"
                
                log(f"🎯 Usando columna de tensión: '{columna_tension}' (proyecto: {tension_proyecto} kV)")
                
                # Convertir columnas de cantidad a numérico
                df[columna_tension] = pd.to_numeric(df[columna_tension], errors='coerce').fillna(0)
                df[columna_opuesta] = pd.to_numeric(df[columna_opuesta], errors='coerce').fillna(0)
                
                # Filtrar materiales con cantidad > 0 en la tensión del proyecto
                df_filtrado = df[df[columna_tension] > 0][["MATERIALES", "UNIDAD", columna_tension]].copy()
                
                log(f"📝 Materiales de '{estructura}' para {tension_proyecto} kV:")
                if df_filtrado.empty:
                    log(f"   ⚠️ No hay materiales con cantidad > 0 en columna '{columna_tension}'")
                else:
                    for _, fila in df_filtrado.iterrows():
                        log(f"   - {fila['MATERIALES']} | {fila['UNIDAD']} | {fila[columna_tension]}")
                
                # Mostrar también qué habría en la otra tensión para comparación
                df_otra_tension = df[df[columna_opuesta] > 0][["MATERIALES", "UNIDAD", columna_opuesta]].copy()
                if not df_otra_tension.empty:
                    log(f"📝 Materiales que tendría en {columna_opuesta} kV:")
                    for _, fila in df_otra_tension.iterrows():
                        log(f"   - {fila['MATERIALES']} | {fila['UNIDAD']} | {fila[columna_opuesta]}")

                # Aplicar reemplazos de conectores si hay materiales
                if not df_filtrado.empty:
                    materiales_lista = df_filtrado["MATERIALES"].astype(str).tolist()
                    materiales_reemplazados = aplicar_reemplazos_conectores(
                        materiales_lista, calibre_primario, tabla_conectores_mt
                    )
                    
                    df_filtrado["Materiales"] = materiales_reemplazados
                    df_filtrado["Unidad"] = df_filtrado["UNIDAD"]
                    df_filtrado["Cantidad"] = df_filtrado[columna_tension] * cant

                    df_total = pd.concat([df_total, df_filtrado[["Materiales", "Unidad", "Cantidad"]]])
                    log(f"✅ Materiales agregados para '{estructura}': {len(df_filtrado)} filas")
                else:
                    log(f"⚠️ No se agregaron materiales para '{estructura}' - cantidad 0 en {tension_proyecto} kV")
                
            except Exception as e:
                log(f"❌ Error al procesar materiales de '{estructura}': {e}")
                continue
                
        except Exception as e:
            log(f"❌ Error al procesar hoja '{estructura}': {e}")

    # --- Materiales adicionales ---
    if archivo_estructuras:
        try:
            df_adicionales = cargar_adicionales(archivo_estructuras)
            if not df_adicionales.empty:
                df_total = pd.concat([df_total, df_adicionales[["Materiales", "Unidad", "Cantidad"]]])
                log(f"📌 Materiales adicionales agregados: {df_adicionales.shape[0]} filas")
        except Exception as e:
            log(f"⚠️ Error al cargar materiales adicionales: {e}")

    # --- Resumen general ---
    if not df_total.empty:
        df_resumen = df_total.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
        log(f"📊 Resumen de materiales totales:")
        for _, fila in df_resumen.iterrows():
            log(f"   - {fila['Materiales']} | {fila['Unidad']} | {fila['Cantidad']}")
    else:
        df_resumen = pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])
        log("⚠️ No se generaron materiales en el resumen general")
    
    # Resumen de estructuras
    df_indice["Cantidad"] = df_indice["NombreEstructura"].map(conteo).fillna(0).astype(int)
    df_estructuras_resumen = df_indice[df_indice["Cantidad"] > 0]

    # --- Resumen por punto ---
    df_resumen_por_punto = pd.DataFrame(columns=["Punto", "Materiales", "Unidad", "Cantidad"])

    log(f"🎯 RESUMEN FINAL: {df_resumen.shape[0]} materiales, {df_estructuras_resumen.shape[0]} estructuras")

    return df_resumen, df_estructuras_resumen, df_resumen_por_punto, datos_proyecto
