# -*- coding: utf-8 -*-
"""
Created on Wed Oct  1 16:54:46 2025

@author: José Nikol Cruz
"""

# -*- coding: utf-8 -*-
"""
procesar_materiales.py
Función para procesar los archivos de estructuras y materiales
y devolver los resúmenes listos para generar reportes.
"""

import pandas as pd
from collections import Counter
from modulo.entradas import (
    cargar_datos_proyecto,
    cargar_estructuras_proyectadas,
    extraer_estructuras_proyectadas,
    cargar_indice,
    cargar_adicionales,
    cargar_materiales
)
from modulo.conectores_mt import (
    cargar_conectores_mt,
    aplicar_reemplazos_conectores
)

def procesar_materiales(archivo_estructuras=None, archivo_materiales=None, estructuras_df=None):
    """
    Procesa los archivos Excel de estructuras y materiales, o un DataFrame de estructuras,
    y devuelve los DataFrames de resúmenes listos para exportar.

    Parámetros:
    - archivo_estructuras: ruta al archivo Excel de estructuras (opcional si estructuras_df se pasa)
    - archivo_materiales: ruta al archivo Excel con base de datos de materiales (requerido)
    - estructuras_df: DataFrame con estructuras proyectadas (opcional)

    Retorna:
    - df_resumen, df_estructuras_resumen, df_resumen_por_punto, datos_proyecto
    """

    # --- Datos del proyecto ---
    if archivo_estructuras is not None:
        datos_proyecto = cargar_datos_proyecto(archivo_estructuras)
        df_estructuras = cargar_estructuras_proyectadas(archivo_estructuras)
    elif estructuras_df is not None:
        # Si solo se recibe DataFrame, no hay datos_proyecto ni archivo para cargarlos
        datos_proyecto = {}
        df_estructuras = estructuras_df.copy()
    else:
        raise ValueError("Debe proporcionar archivo_estructuras o estructuras_df")

    nombre_proyecto = datos_proyecto.get("nombre_proyecto", "Proyecto")
    tension = datos_proyecto.get("nivel_de_tension") or datos_proyecto.get("tension")
    calibre_primario = datos_proyecto.get("calibre_primario", "1/0 ASCR")

    # Normalizar tensión
    if tension:
        tension = str(tension).replace(",", ".").replace("kV", "").strip()

    # --- Estructuras proyectadas ---
    estructuras_proyectadas, estructuras_por_punto = extraer_estructuras_proyectadas(df_estructuras)
    from collections import Counter
    conteo = Counter(estructuras_proyectadas)

    # --- Índice y conectores ---
    df_indice = cargar_indice(archivo_materiales)
    tabla_conectores_mt = cargar_conectores_mt(archivo_materiales)

    # =================== PROCESAMIENTO ===================
    import pandas as pd
    df_total = pd.DataFrame()

    for estructura, cant in conteo.items():
        try:
            df_temp = cargar_materiales(archivo_materiales, estructura, header=None)
            fila_tension = next(
                i for i, row in df_temp.iterrows() if any(str(tension) in str(cell) for cell in row)
            )
            df = cargar_materiales(archivo_materiales, estructura, header=fila_tension)

            # 🔧 Normalizar cabeceras
            df.columns = df.columns.map(lambda x: str(x).strip())

            if "Materiales" not in df.columns or tension not in df.columns:
                continue

            unidad_col = df.columns[df.columns.get_loc("Materiales") + 1]
            df_filtrado = df[df[tension] > 0][["Materiales", unidad_col, tension]].copy()

            # ✅ Reemplazo conectores MT
            df_filtrado["Materiales"] = aplicar_reemplazos_conectores(
                df_filtrado["Materiales"].tolist(),
                calibre_primario,
                tabla_conectores_mt
            )

            df_filtrado["Unidad"] = df_filtrado[unidad_col]
            df_filtrado["Cantidad"] = df_filtrado[tension] * cant
            df_total = pd.concat([df_total, df_filtrado[["Materiales", "Unidad", "Cantidad"]]])
        except Exception as e:
            print(f"⚠️ Error en estructura {estructura}: {e}")

    # --- Materiales adicionales ---
    if archivo_estructuras is not None:
        df_adicionales = cargar_adicionales(archivo_estructuras)
        df_total = pd.concat([df_total, df_adicionales[["Materiales", "Unidad", "Cantidad"]]])

    # --- Resúmenes ---
    df_resumen = df_total.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
    df_indice["Cantidad"] = df_indice["NombreEstructura"].map(conteo).fillna(0).astype(int)
    df_estructuras_resumen = df_indice[df_indice["Cantidad"] > 0]

    # --- Resumen por punto ---
    resumen_punto = []
    for punto, estructuras in estructuras_por_punto.items():
        for est in estructuras:
            try:
                df_temp = cargar_materiales(archivo_materiales, est, header=None)
                fila_tension = next(
                    i for i, row in df_temp.iterrows() if any(str(tension) in str(cell) for cell in row)
                )
                df = cargar_materiales(archivo_materiales, est, header=fila_tension)

                df.columns = df.columns.map(lambda x: str(x).strip())
                unidad_col = df.columns[df.columns.get_loc("Materiales") + 1]
                dfp = df[df[tension] > 0][["Materiales", unidad_col, tension]].copy()
                dfp["Unidad"] = dfp[unidad_col]
                dfp["Cantidad"] = dfp[tension]
                dfp["Punto"] = punto
                resumen_punto.append(dfp[["Punto", "Materiales", "Unidad", "Cantidad"]])
            except Exception as e:
                print(f"⚠️ Error en estructura {est}: {e}")

    df_resumen_por_punto = (
        pd.concat(resumen_punto, ignore_index=True)
        .groupby(["Punto", "Materiales", "Unidad"], as_index=False)["Cantidad"]
        .sum()
    )

    return df_resumen, df_estructuras_resumen, df_resumen_por_punto, datos_proyecto

    # --- Estructuras proyectadas ---
    df_estructuras = cargar_estructuras_proyectadas(archivo_estructuras)
    estructuras_proyectadas, estructuras_por_punto = extraer_estructuras_proyectadas(df_estructuras)
    conteo = Counter(estructuras_proyectadas)

    # --- Índice y conectores ---
    df_indice = cargar_indice(archivo_materiales)
    tabla_conectores_mt = cargar_conectores_mt(archivo_materiales)

    # =================== PROCESAMIENTO ===================
    df_total = pd.DataFrame()

    for estructura, cant in conteo.items():
        try:
            df_temp = cargar_materiales(archivo_materiales, estructura, header=None)
            fila_tension = next(
                i for i, row in df_temp.iterrows() if any(str(tension) in str(cell) for cell in row)
            )
            df = cargar_materiales(archivo_materiales, estructura, header=fila_tension)

            # 🔧 Normalizar cabeceras
            df.columns = df.columns.map(lambda x: str(x).strip())

            if "Materiales" not in df.columns or tension not in df.columns:
                continue

            unidad_col = df.columns[df.columns.get_loc("Materiales") + 1]
            df_filtrado = df[df[tension] > 0][["Materiales", unidad_col, tension]].copy()

            # ✅ Reemplazo conectores MT
            df_filtrado["Materiales"] = aplicar_reemplazos_conectores(
                df_filtrado["Materiales"].tolist(),
                calibre_primario,
                tabla_conectores_mt
            )

            df_filtrado["Unidad"] = df_filtrado[unidad_col]
            df_filtrado["Cantidad"] = df_filtrado[tension] * cant
            df_total = pd.concat([df_total, df_filtrado[["Materiales", "Unidad", "Cantidad"]]])
        except Exception as e:
            print(f"⚠️ Error en estructura {estructura}: {e}")

    # --- Materiales adicionales ---
    df_adicionales = cargar_adicionales(archivo_estructuras)
    df_total = pd.concat([df_total, df_adicionales[["Materiales", "Unidad", "Cantidad"]]])

    # --- Resúmenes ---
    df_resumen = df_total.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
    df_indice["Cantidad"] = df_indice["NombreEstructura"].map(conteo).fillna(0).astype(int)
    df_estructuras_resumen = df_indice[df_indice["Cantidad"] > 0]

    # --- Resumen por punto ---
    resumen_punto = []
    for punto, estructuras in estructuras_por_punto.items():
        for est in estructuras:
            try:
                df_temp = cargar_materiales(archivo_materiales, est, header=None)
                fila_tension = next(
                    i for i, row in df_temp.iterrows() if any(str(tension) in str(cell) for cell in row)
                )
                df = cargar_materiales(archivo_materiales, est, header=fila_tension)

                df.columns = df.columns.map(lambda x: str(x).strip())
                unidad_col = df.columns[df.columns.get_loc("Materiales") + 1]
                dfp = df[df[tension] > 0][["Materiales", unidad_col, tension]].copy()
                dfp["Unidad"] = dfp[unidad_col]
                dfp["Cantidad"] = dfp[tension]
                dfp["Punto"] = punto
                resumen_punto.append(dfp[["Punto", "Materiales", "Unidad", "Cantidad"]])
            except Exception as e:
                print(f"⚠️ Error en estructura {est}: {e}")

    df_resumen_por_punto = (
        pd.concat(resumen_punto, ignore_index=True)
        .groupby(["Punto", "Materiales", "Unidad"], as_index=False)["Cantidad"]
        .sum()
    )

    return df_resumen, df_estructuras_resumen, df_resumen_por_punto, datos_proyecto


