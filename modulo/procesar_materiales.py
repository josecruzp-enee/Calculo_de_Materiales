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


def procesar_materiales(archivo_estructuras=None, archivo_materiales=None, estructuras_df=None, datos_proyecto=None):
    if archivo_estructuras:
        datos_proyecto = cargar_datos_proyecto(archivo_estructuras)
        df_estructuras = cargar_estructuras_proyectadas(archivo_estructuras)
    elif estructuras_df is not None:
        datos_proyecto = datos_proyecto or {}
        df_estructuras = estructuras_df.copy()
    else:
        raise ValueError("Debe proporcionar archivo_estructuras o estructuras_df")

    tension, calibre_mt = validar_datos_proyecto(datos_proyecto)
    if not tension or not calibre_mt:
        return (
            pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"]),
            pd.DataFrame(columns=["NombreEstructura", "Cantidad"]),
            pd.DataFrame(columns=["Punto", "Materiales", "Unidad", "Cantidad"]),
            datos_proyecto
        )

    conteo, estructuras_por_punto = extraer_conteo_estructuras(df_estructuras)
    df_indice = cargar_indice(archivo_materiales)
    tabla_conectores_mt = cargar_conectores_mt(archivo_materiales)

    df_total = pd.concat(
        [calcular_materiales_estructura(archivo_materiales, e, c, tension, calibre_mt, tabla_conectores_mt)
         for e, c in conteo.items()],
        ignore_index=True
    )

    if archivo_estructuras:
        df_adicionales = cargar_adicionales(archivo_estructuras)
        df_total = pd.concat([df_total, df_adicionales], ignore_index=True)

    df_resumen = df_total.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum() if not df_total.empty else pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])
    df_indice["Cantidad"] = df_indice["NombreEstructura"].map(conteo).fillna(0).astype(int)
    df_estructuras_resumen = df_indice[df_indice["Cantidad"] > 0]
    df_resumen_por_punto = calcular_materiales_por_punto(archivo_materiales, estructuras_por_punto, tension)

    return df_resumen, df_estructuras_resumen, df_resumen_por_punto, datos_proyecto
