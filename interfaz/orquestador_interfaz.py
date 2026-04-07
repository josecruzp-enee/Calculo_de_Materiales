# -*- coding: utf-8 -*-
# interfaz/orquestador_interfaz.py

import streamlit as st

# =========================================================
# IMPORTS UI (SEGUROS)
# =========================================================
from interfaz.base import seleccionar_modo_carga

from interfaz.datos_proyecto import seccion_datos_proyecto
from interfaz.cables_ui import seccion_cables
from interfaz.estructuras_ui import seccion_entrada_estructuras

from interfaz.exportacion_ui import (
    seccion_finalizar_calculo,
    seccion_exportacion,
)

# 🔒 IMPORT PROTEGIDO (no rompe si no existe)
try:
    from interfaz.materiales_extra import obtener_materiales_finales
except Exception:
    def obtener_materiales_finales():
        return None


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
    st.session_state.setdefault("ruta_estructuras_compacto", None)


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
# ESTRUCTURAS (MULTIMODO REAL)
# =========================================================
def renderizar_estructuras():

    modo = st.session_state.get("modo_carga_seleccionado")

    if not modo:
        st.warning("⚠️ Primero selecciona el modo de carga.")
        return

    archivo = None
    df_ui = None

    try:

        # -------------------------
        # MANUAL (UI)
        # -------------------------
        if modo == "manual":
            df, _ = seccion_entrada_estructuras()

            if df is None or df.empty:
                return

            df_ui = df

        # -------------------------
        # EXCEL
        # -------------------------
        elif modo == "excel":
            archivo = st.file_uploader("Subir Excel", type=["xlsx"])

        # -------------------------
        # TABLA
        # -------------------------
        elif modo == "tabla":
            archivo = st.text_area("Pegar tabla")

        # -------------------------
        # PDF
        # -------------------------
        elif modo == "pdf":
            archivo = st.file_uploader("Subir PDF", type=["pdf"])

        # -------------------------
        # DXF
        # -------------------------
        elif modo == "dxf":
            archivo = st.file_uploader("Subir DXF", type=["dxf"])

        else:
            st.warning(f"Modo no soportado: {modo}")
            return

    except Exception as e:
        st.error(f"Error en carga: {e}")
        return

    # =========================
    # GUARDAR ENTRADA CRUDA
    # =========================
    st.session_state["tipo_entrada"] = modo

    if df_ui is not None:
        st.session_state["data_entrada"] = df_ui
    else:
        st.session_state["data_entrada"] = archivo

    st.success(f"Entrada cargada correctamente ({modo})")
# =========================================================
# FINAL (SIN LÓGICA DE NEGOCIO)
# =========================================================
def renderizar_final():

    df = st.session_state.get("df_estructuras")

    if not es_dataframe_valido(df):
        st.warning("⚠️ Carga estructuras primero.")
        return

    st.session_state["df_materiales_extra"] = obtener_materiales_finales()

    seccion_finalizar_calculo()


def renderizar_exportacion():

    df = st.session_state.get("df_estructuras")

    if not es_dataframe_valido(df):
        st.warning("⚠️ Primero completa estructuras.")
        return

    st.session_state["df_materiales_extra"] = obtener_materiales_finales()

    seccion_exportacion()


# =========================================================
# ORQUESTADOR PRINCIPAL (UI PURO)
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
        st.warning("Sección no reconocida.")
