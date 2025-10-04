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
    if archivo_estructuras:
        datos_proyecto = cargar_datos_proyecto(archivo_estructuras)
        df_estructuras = cargar_estructuras_proyectadas(archivo_estructuras)
    elif estructuras_df is not None:
        datos_proyecto = datos_proyecto or {}
        df_estructuras = estructuras_df.copy()
    else:
        raise ValueError("Debe proporcionar archivo_estructuras o estructuras_df")

    # 1️⃣ Validar
    tension, calibre_mt = validar_datos_proyecto(datos_proyecto)
    print(">>> Tensión:", tension, "Calibre MT:", calibre_mt)

    # 2️⃣ Conteo estructuras
    conteo, estructuras_por_punto = extraer_conteo_estructuras(df_estructuras)
    print(">>> Conteo estructuras:", conteo)
    print(">>> Estructuras por punto:", estructuras_por_punto)

    # 3️⃣ Cargar índice
    df_indice = cargar_indice(archivo_materiales)
    print(">>> Columnas originales índice:", df_indice.columns.tolist())

    df_indice.columns = df_indice.columns.str.strip().str.lower()
    print(">>> Columnas normalizadas índice:", df_indice.columns.tolist())
    print(">>> Primeras filas índice:\n", df_indice.head(10))

    # 4️⃣ Conectores
    tabla_conectores_mt = cargar_conectores_mt(archivo_materiales)

    # 5️⃣ Materiales por estructura
    df_total = pd.concat(
        [
            calcular_materiales_estructura(
                archivo_materiales, e, c, tension, calibre_mt, tabla_conectores_mt
            )
            for e, c in conteo.items()
        ],
        ignore_index=True
    )
    print(">>> df_total (materiales por estructura):\n", df_total.head(10))

    # 6️⃣ Resumen global materiales
    df_resumen = (
        df_total.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
        if not df_total.empty
        else pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])
    )
    print(">>> df_resumen (materiales):\n", df_resumen.head(10))

    # 7️⃣ Resumen de estructuras globales
    if "codigodeestructura" not in df_indice.columns:
        df_indice["codigodeestructura"] = None

    # Normalizar claves
    df_indice["codigodeestructura"] = df_indice["codigodeestructura"].str.strip().str.upper()
    conteo = {k.strip().upper(): v for k,v in conteo.items()}

    df_indice["Cantidad"] = df_indice["codigodeestructura"].map(conteo).fillna(0).astype(int)
    df_estructuras_resumen = df_indice[df_indice["Cantidad"] > 0]
    print(">>> df_estructuras_resumen:\n", df_estructuras_resumen.head(10))

    # 8️⃣ Estructuras por punto
    lista_por_punto = []
    for punto, estructuras in estructuras_por_punto.items():
        for est in estructuras:
            est_norm = est.strip().upper()
            lista_por_punto.append({
                "Punto": punto,
                "codigodeestructura": est_norm,
                "Descripcion": df_indice.loc[
                    df_indice["codigodeestructura"] == est_norm, "descripcion"
                ].values[0] if est_norm in df_indice["codigodeestructura"].values else "NO ENCONTRADA",
                "Cantidad": 1
            })
    df_estructuras_por_punto = pd.DataFrame(lista_por_punto)
    print(">>> df_estructuras_por_punto:\n", df_estructuras_por_punto.head(10))

    # 9️⃣ Materiales por punto
    df_resumen_por_punto = calcular_materiales_por_punto(
        archivo_materiales, estructuras_por_punto, tension
    )
    print(">>> df_resumen_por_punto:\n", df_resumen_por_punto.head(10))

    return (
        df_resumen,
        df_estructuras_resumen,
        df_estructuras_por_punto,
        df_resumen_por_punto,
        datos_proyecto
    )
