# -*- coding: utf-8 -*-
# interfaz/orquestador_interfaz.py

import streamlit as st

from interfaz.base import seleccionar_modo_carga

from interfaz.datos_proyecto import seccion_datos_proyecto
from interfaz.cables_ui import seccion_cables
from interfaz.estructuras_ui import seccion_entrada_estructuras

from interfaz.exportacion_ui import (
    seccion_finalizar_calculo,
    seccion_exportacion,
)

from interfaz.materiales_extra import obtener_materiales_finales


# =========================================================
# HELPERS
# =========================================================
def es_dataframe_valido(df):
    return df is not None and hasattr(df, "empty") and not df.empty


def _init_state():
    st.session_state.setdefault("df_estructuras", None)
    st.session_state.setdefault("modo_carga_seleccionado", None)
    st.session_state.setdefault("cables_proyecto_df", None)
    st.session_state.setdefault("datos_proyecto", None)
    st.session_state.setdefault("df_materiales_extra", None)


# =========================================================
# SECCIONES UI
# =========================================================

def renderizar_datos_proyecto():
    datos = seccion_datos_proyecto()
    if datos:
        st.session_state["datos_proyecto"] = datos


def renderizar_cables():
    cables = seccion_cables()
    if cables is not None:
        st.session_state["cables_proyecto_df"] = cables


def renderizar_modo_carga():
    st.subheader("3) Modo de Carga")

    modo = seleccionar_modo_carga()

    mapa = {
        "Desde archivo Excel": "excel",
        "Pegar tabla": "tabla",
        "Listas desplegables": "manual",
        "Pdf": "pdf",
        "DXF (ENEE)": "dxf",
    }

    st.session_state["modo_carga_seleccionado"] = mapa.get(modo, modo)


def renderizar_estructuras():

    modo = st.session_state.get("modo_carga_seleccionado")

    if not modo:
        st.warning("⚠️ Primero selecciona el modo de carga.")
        return

    if modo != "manual":
        st.info("⚠️ Por ahora solo está activo modo desplegables.")
        return

    df, ruta = seccion_entrada_estructuras()

    if not es_dataframe_valido(df):
        st.info("⚠️ No hay estructuras aún.")
        return

    st.session_state["df_estructuras"] = df
    st.session_state["ruta_estructuras_compacto"] = ruta

    st.success("✅ Estructuras listas.")


def renderizar_final():

    df = st.session_state.get("df_estructuras")

    if not es_dataframe_valido(df):
        st.warning("⚠️ Carga estructuras primero.")
        return

    # =========================
    # NORMALIZAR ENTRADAS UI
    # =========================
    df_cables = st.session_state.get("cables_proyecto_df")
    datos_proyecto = st.session_state.get("datos_proyecto")

    # 🔥 MATERIAL EXTRA SIEMPRE CONSOLIDADO
    df_materiales_extra = obtener_materiales_finales()
    st.session_state["df_materiales_extra"] = df_materiales_extra

    # =========================
    # LLAMADA A CAPA APLICACIÓN
    # =========================
    seccion_finalizar_calculo(
        df_estructuras=df,
        df_cables=df_cables,
        datos_proyecto=datos_proyecto,
        df_materiales_extra=df_materiales_extra,
    )


def renderizar_exportacion():

    df = st.session_state.get("df_estructuras")

    if not es_dataframe_valido(df):
        st.warning("⚠️ Primero completa estructuras.")
        return

    # 🔥 asegurar consistencia antes de exportar
    st.session_state["df_materiales_extra"] = obtener_materiales_finales()

    seccion_exportacion()


# =========================================================
# ORQUESTADOR PRINCIPAL
# =========================================================

def ejecutar_orquestador_interfaz(
    _nav_estado_actual,
    _barra_nav_botones,
):

    # =========================
    # INIT GLOBAL STATE
    # =========================
    _init_state()

    # =========================
    # NAVEGACIÓN
    # =========================
    seccion = _nav_estado_actual()
    _barra_nav_botones(seccion)

    # =========================
    # MAPA DE SECCIONES
    # =========================
    acciones = {
        "datos": renderizar_datos_proyecto,
        "cables": renderizar_cables,
        "modo": renderizar_modo_carga,
        "estructuras": renderizar_estructuras,
        "final": renderizar_final,
        "exportar": renderizar_exportacion,
    }

    funcion = acciones.get(seccion)

    if funcion:
        funcion()
    else:
        st.warning("⚠️ Sección no reconocida.")
