# -*- coding: utf-8 -*-
import pandas as pd
from modulo.entradas import (
    cargar_datos_proyecto,
    cargar_estructuras_proyectadas,
    cargar_indice,
    cargar_adicionales,
)
from modulo.conectores_mt import cargar_conectores_mt
from modulo.materiales_validacion import validar_datos_proyecto
from modulo.materiales_estructuras import extraer_conteo_estructuras, calcular_materiales_estructura
from modulo.materiales_puntos import calcular_materiales_por_punto

try:
    import streamlit as st
    log = st.write
except ImportError:
    log = print


def procesar_materiales(
    archivo_estructuras=None,
    archivo_materiales=None,
    estructuras_df=None,
    datos_proyecto=None
):
    """
    Procesa materiales de un proyecto eléctrico.
    Retorna:
      - df_resumen: resumen global de materiales
      - df_estructuras_resumen: resumen de estructuras globales
      - df_estructuras_por_punto: estructuras agrupadas por punto
      - df_resumen_por_punto: materiales agrupados por punto
      - datos_proyecto: metadatos del proyecto
    """

    # 1️⃣ Cargar estructuras base
    if archivo_estructuras:
        datos_proyecto = cargar_datos_proyecto(archivo_estructuras)
        df_estructuras = cargar_estructuras_proyectadas(archivo_estructuras)
    elif estructuras_df is not None:
        datos_proyecto = datos_proyecto or {}
        df_estructuras = estructuras_df.copy()
    else:
        raise ValueError("Debe proporcionar archivo_estructuras o estructuras_df")

    # 2️⃣ Validar datos del proyecto
    tension, calibre_mt = validar_datos_proyecto(datos_proyecto)
    if not tension or not calibre_mt:
        return (
            pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"]),
            pd.DataFrame(columns=["CodigoEstructura", "Descripcion", "Cantidad"]),
            pd.DataFrame(columns=["Punto", "codigodeestructura", "Descripcion", "Cantidad"]),
            pd.DataFrame(columns=["Punto", "Materiales", "Unidad", "Cantidad"]),
            datos_proyecto
        )

    # 3️⃣ Conteo de estructuras
    conteo, estructuras_por_punto = extraer_conteo_estructuras(df_estructuras)

    # 4️⃣ Cargar índice
    df_indice = cargar_indice(archivo_materiales)
    df_indice.columns = df_indice.columns.str.strip()
    df_indice.rename(columns={"Código de Estructura": "codigodeestructura"}, inplace=True)

    # 5️⃣ Cargar conectores
    tabla_conectores_mt = cargar_conectores_mt(archivo_materiales)

    # 6️⃣ Calcular materiales por estructura
    df_total = pd.concat(
        [
            calcular_materiales_estructura(
                archivo_materiales, e, c, tension, calibre_mt, tabla_conectores_mt
            )
            for e, c in conteo.items()
        ],
        ignore_index=True
    )

    # Agregar adicionales desde archivo si existen
    if archivo_estructuras:
        df_adicionales = cargar_adicionales(archivo_estructuras)
        df_total = pd.concat([df_total, df_adicionales], ignore_index=True)

    # 7️⃣ Resumen global de materiales
    df_resumen = (
        df_total.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
        if not df_total.empty
        else pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])
    )

    # 8️⃣ Resumen de estructuras globales
    if "codigodeestructura" not in df_indice.columns:
        df_indice["codigodeestructura"] = None
    df_indice["Cantidad"] = df_indice["codigodeestructura"].map(conteo).fillna(0).astype(int)
    df_estructuras_resumen = df_indice[df_indice["Cantidad"] > 0]

    # 9️⃣ Estructuras por punto (nuevo)
    lista_por_punto = []
    for punto, estructuras in estructuras_por_punto.items():
        for est in estructuras:
            lista_por_punto.append({
                "Punto": punto,
                "codigodeestructura": est,
                "Descripcion": df_indice.loc[df_indice["codigodeestructura"] == est, "Descripcion"].values[0]
                if est in df_indice["codigodeestructura"].values else "",
                "Cantidad": 1
            })
    df_estructuras_por_punto = pd.DataFrame(lista_por_punto)

    # 🔟 Materiales por punto
    df_resumen_por_punto = calcular_materiales_por_punto(
        archivo_materiales, estructuras_por_punto, tension
    )

    # Debug opcional
    log(f"📋 Columnas en df_indice: {df_indice.columns.tolist()}")
    log(f"🔢 Conteo estructuras: {len(conteo)}")
    log(f"📊 Resumen materiales: {len(df_resumen)} filas")
    log(f"📊 Resumen estructuras: {len(df_estructuras_resumen)} filas")
    log(f"📊 Estructuras por punto: {len(df_estructuras_por_punto)} filas")
    log(f"📊 Materiales por punto: {len(df_resumen_por_punto)} filas")

    return (
        df_resumen,
        df_estructuras_resumen,
        df_estructuras_por_punto,
        df_resumen_por_punto,
        datos_proyecto
    )
