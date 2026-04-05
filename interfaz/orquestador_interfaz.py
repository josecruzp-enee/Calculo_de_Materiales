# -*- coding: utf-8 -*-
# interfaz/orquestador_interfaz.py

import streamlit as st

from interfaz.base import (
    seleccionar_modo_carga,
    ruta_datos_materiales_por_defecto,
)

from interfaz.datos_proyecto import seccion_datos_proyecto
from interfaz.cables_ui import seccion_cables  # ✅ CAMBIO CLAVE

from interfaz.estructuras import seccion_entrada_estructuras
from interfaz.materiales_extra import seccion_adicionar_material

from interfaz.exportacion import (
    seccion_finalizar_calculo,
    seccion_exportacion,
)

from interfaz.mapa_kml import seccion_mapa_kmz


# =========================================================
# HELPERS
# =========================================================

def es_dataframe_valido(df):
    return df is not None and hasattr(df, "empty") and not df.empty


# =========================================================
# SECCIONES UI (SIN LÓGICA)
# =========================================================

def renderizar_datos_proyecto():
    seccion_datos_proyecto()


def renderizar_cables():
    # ⚠️ UI directa → maneja su propio session_state
    seccion_cables()


def renderizar_modo_carga():
    st.subheader("3) Modo de Carga")

    modo = seleccionar_modo_carga()
    st.session_state["modo_carga_seleccionado"] = modo


def renderizar_estructuras():

    if "modo_carga_seleccionado" not in st.session_state:
        st.warning("⚠️ Primero selecciona el modo de carga.")
        return

    modo = st.session_state["modo_carga_seleccionado"]

    df, ruta = seccion_entrada_estructuras(modo)

    if not es_dataframe_valido(df):
        st.warning("⚠️ No se generaron estructuras.")
        return

    # ✔ SOLO almacenar resultado
    st.session_state["df_estructuras"] = df
    st.session_state["ruta_estructuras_compacto"] = ruta

    st.success("✅ Estructuras cargadas correctamente.")


def renderizar_materiales():
    seccion_adicionar_material()


def renderizar_final():

    df = st.session_state.get("df_estructuras")

    if not es_dataframe_valido(df):
        st.info("⚠️ Carga estructuras primero.")
        return

    seccion_finalizar_calculo(df)


def renderizar_exportacion():

    df = st.session_state.get("df_estructuras")
    ruta = st.session_state.get("ruta_estructuras_compacto")

    if not es_dataframe_valido(df):
        st.warning("⚠️ Primero completa estructuras.")
        return

    seccion_exportacion(
        df=df,
        modo_carga=st.session_state.get("modo_carga_seleccionado"),
        ruta_estructuras=ruta,
        ruta_datos_materiales=ruta_datos_materiales_por_defecto(),
    )


def renderizar_mapa():
    seccion_mapa_kmz()


# =========================================================
# ORQUESTADOR PRINCIPAL
# =========================================================

def ejecutar_orquestador_interfaz(
    _nav_estado_actual,
    _barra_nav_botones,
):

    seccion = _nav_estado_actual()

    # Dibujar barra de navegación
    _barra_nav_botones(seccion)

    # Mapa de navegación → UI pura
    acciones = {
        "datos": renderizar_datos_proyecto,
        "cables": renderizar_cables,
        "modo": renderizar_modo_carga,
        "estructuras": renderizar_estructuras,
        "materiales": renderizar_materiales,
        "final": renderizar_final,
        "exportar": renderizar_exportacion,
        "mapa_kml": renderizar_mapa,
    }

    funcion = acciones.get(seccion)

    if funcion:
        funcion()
    else:
        st.warning("⚠️ Sección no reconocida.")
