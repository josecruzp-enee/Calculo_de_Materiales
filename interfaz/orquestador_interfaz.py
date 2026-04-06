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


# =========================================================
# 🔥 FUNCIÓN MULTI-MODO CORREGIDA
# =========================================================
def renderizar_estructuras():

    modo = st.session_state.get("modo_carga_seleccionado")

    if not modo:
        st.warning("⚠️ Primero selecciona el modo de carga.")
        return

    df = None
    ruta = None

    # -------------------------
    # MANUAL
    # -------------------------
    if modo == "manual":
        try:
            df, ruta = seccion_entrada_estructuras()
        except Exception as e:
            st.error(f"❌ Error en modo manual: {e}")
            return

    # -------------------------
    # EXCEL
    # -------------------------
    elif modo == "excel":
        try:
            from entradas.leer_excel import leer_excel
            df, ruta = leer_excel()
        except Exception as e:
            st.error(f"❌ Error en Excel: {e}")
            return

    # -------------------------
    # TABLA
    # -------------------------
    elif modo == "tabla":
        try:
            from entradas.entradas_tabla import leer_tabla
            df, ruta = leer_tabla()
        except Exception as e:
            st.error(f"❌ Error en Tabla: {e}")
            return

    # -------------------------
    # PDF
    # -------------------------
    elif modo == "pdf":
        try:
            from entradas.entradas_pdf import leer_pdf
            df, ruta = leer_pdf()
        except Exception as e:
            st.error(f"❌ Error en PDF: {e}")
            return

    # -------------------------
    # DXF
    # -------------------------
    elif modo == "dxf":
        try:
            from entradas.entradas_dxf import leer_dxf
            df, ruta = leer_dxf()
        except Exception as e:
            st.error(f"❌ Error en DXF: {e}")
            return

    else:
        st.warning(f"⚠️ Modo no soportado: {modo}")
        return

    # -------------------------
    # VALIDACIÓN
    # -------------------------
    if df is None:
        st.error("❌ No se pudo cargar información.")
        return

    if not hasattr(df, "empty"):
        st.error("❌ Resultado inválido (no es DataFrame).")
        return

    if df.empty:
        st.info("⚠️ No hay estructuras aún.")
        return

    # -------------------------
    # GUARDAR ESTADO
    # -------------------------
    st.session_state["df_estructuras"] = df
    st.session_state["ruta_estructuras_compacto"] = ruta

    st.success(f"✅ Estructuras cargadas desde modo: {modo}")


def renderizar_final():

    df = st.session_state.get("df_estructuras")

    if not es_dataframe_valido(df):
        st.warning("⚠️ Carga estructuras primero.")
        return

    df_cables = st.session_state.get("cables_proyecto_df")
    datos_proyecto = st.session_state.get("datos_proyecto")

    df_materiales_extra = obtener_materiales_finales()
    st.session_state["df_materiales_extra"] = df_materiales_extra

    seccion_finalizar_calculo()


def renderizar_exportacion():

    df = st.session_state.get("df_estructuras")

    if not es_dataframe_valido(df):
        st.warning("⚠️ Primero completa estructuras.")
        return

    st.session_state["df_materiales_extra"] = obtener_materiales_finales()

    seccion_exportacion()


# =========================================================
# ORQUESTADOR PRINCIPAL
# =========================================================

def ejecutar_orquestador_interfaz(
    _nav_estado_actual,
    _barra_nav_botones,
):

    _init_state()

    seccion = _nav_estado_actual()
    _barra_nav_botones(seccion)

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
