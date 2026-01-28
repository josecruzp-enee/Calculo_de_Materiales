# -*- coding: utf-8 -*-
"""
calculo_materiales.py
Orquestador: calcula materiales globales y por punto.
Devuelve dict 'resultados' con DFs + datos_proyecto.
"""

import pandas as pd

from modulo.entradas import (
    cargar_datos_proyecto,
    cargar_estructuras_proyectadas,
)

# ✅ SOLO necesitamos cargar la tabla de conectores MT
from core.conectores_mt import cargar_conectores_mt

from core.materiales_validacion import validar_datos_proyecto
from core.materiales_estructuras import calcular_materiales_estructura

from servicios.normalizacion_estructuras import (
    get_logger,
    normalizar_datos_proyecto,
    extraer_tension_ll_kv,
    limpiar_df_estructuras,
    construir_estructuras_por_punto_y_conteo,
)

from servicios.indice_estructuras import (
    cargar_indice_normalizado,
    construir_df_estructuras_resumen,
    construir_df_estructuras_por_punto,
)

from servicios.materiales_por_punto import (
    calcular_materiales_por_punto_con_cantidad,
)


def integrar_materiales_extra(df_resumen: pd.DataFrame, datos_proyecto: dict, log):
    """
    Integra materiales extra desde session_state.
    ✅ NO normaliza nombres (ya vienen uniformes).
    """
    try:
        import streamlit as st  # noqa
        materiales_extra = st.session_state.get("materiales_extra", [])
    except Exception:
        materiales_extra = []

    if materiales_extra:
        df_extra = pd.DataFrame(materiales_extra)

        df_out = pd.concat([df_resumen, df_extra], ignore_index=True)
        df_out = df_out.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

        datos_proyecto["materiales_extra"] = df_extra
        log(f"✅ Se integraron {len(df_extra)} materiales adicionales manuales")
        return df_out, datos_proyecto

    datos_proyecto["materiales_extra"] = pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])
    return df_resumen, datos_proyecto


def calcular_materiales(
    archivo_estructuras=None,
    archivo_materiales=None,
    estructuras_df=None,
    datos_proyecto=None
):
    log = get_logger()

    if archivo_estructuras:
        if not datos_proyecto:
            datos_proyecto = cargar_datos_proyecto(archivo_estructuras)
        df_estructuras = cargar_estructuras_proyectadas(archivo_estructuras)
    elif estructuras_df is not None:
        datos_proyecto = datos_proyecto or {}
        df_estructuras = estructuras_df.copy()
    else:
        raise ValueError("Debe proporcionar 'archivo_estructuras' o 'estructuras_df'.")

    datos_proyecto = normalizar_datos_proyecto(datos_proyecto)

    # ✅ Este calibre_mt es el GLOBAL que se define en Streamlit / datos_proyecto
    tension_raw, calibre_mt = validar_datos_proyecto(datos_proyecto)
    log(f"Tensión (raw): {tension_raw}   Calibre MT: {calibre_mt}")

    tension_ll = (
        extraer_tension_ll_kv(tension_raw)
        or extraer_tension_ll_kv(datos_proyecto.get("nivel_de_tension"))
        or extraer_tension_ll_kv(datos_proyecto.get("tension"))
    )
    if tension_ll is None:
        raise ValueError(f"No pude interpretar la tensión. Recibí: {tension_raw!r}")

    log(f"✅ Tensión normalizada (LL kV): {tension_ll}")

    log("🔍 Limpieza inicial de estructuras...")
    df_estructuras_unicas = limpiar_df_estructuras(df_estructuras, log)

    _, conteo, tmp_explotado = construir_estructuras_por_punto_y_conteo(df_estructuras_unicas, log)

    df_indice = cargar_indice_normalizado(archivo_materiales, log)
    tabla_conectores_mt = cargar_conectores_mt(archivo_materiales)

    # === Materiales globales por estructura ===
    df_lista = []
    for e, cantidad in conteo.items():
        # ✅ NO se determina calibre por estructura.
        # ✅ Se usa SIEMPRE el calibre MT global.
        df_mat = calcular_materiales_estructura(
            archivo_materiales, e, cantidad, tension_ll, calibre_mt, tabla_conectores_mt
        )

        if df_mat is not None and not df_mat.empty:
            df_mat["Unidad"] = df_mat["Unidad"].astype(str).str.strip()
            df_lista.append(df_mat)

    df_total = pd.concat(df_lista, ignore_index=True) if df_lista else pd.DataFrame()

    if not df_total.empty:
        df_resumen = df_total.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
    else:
        df_resumen = pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])

    df_estructuras_resumen = construir_df_estructuras_resumen(df_indice, conteo, log)
    df_estructuras_por_punto = construir_df_estructuras_por_punto(tmp_explotado, df_indice, log)

    # === Materiales por punto ===
    df_resumen_por_punto = calcular_materiales_por_punto_con_cantidad(
        archivo_materiales, tmp_explotado, tension_ll, tabla_conectores_mt, datos_proyecto, log=log
    )

    # materiales extra (manuales)
    df_resumen, datos_proyecto = integrar_materiales_extra(df_resumen, datos_proyecto, log)

    return {
        "datos_proyecto": datos_proyecto,
        "tension_ll": tension_ll,
        "calibre_mt": calibre_mt,

        "df_resumen": df_resumen,
        "df_estructuras_resumen": df_estructuras_resumen,
        "df_estructuras_por_punto": df_estructuras_por_punto,
        "df_resumen_por_punto": df_resumen_por_punto,

        # opcional debug
        "conteo": conteo,
        "tmp_explotado": tmp_explotado,
    }
