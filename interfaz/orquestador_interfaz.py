# -*- coding: utf-8 -*-
# interfaz/orquestador_interfaz.py

import streamlit as st

from interfaz.base import (
    seleccionar_modo_carga,
    ruta_datos_materiales_por_defecto,
)

from interfaz.datos_proyecto import seccion_datos_proyecto
from interfaz.cables_ui import seccion_cables
from entradas.entradas_desplegables import cargar_desde_desplegables

from interfaz.exportacion_ui import (
    seccion_finalizar_calculo,
    seccion_exportacion,
)
from interfaz.estructuras_ui import seccion_entrada_estructuras

# =========================================================
# HELPERS
# =========================================================

def es_dataframe_valido(df):
    return df is not None and hasattr(df, "empty") and not df.empty


# =========================================================
# SECCIONES UI (SIN LÓGICA DE NEGOCIO)
# =========================================================

def renderizar_datos_proyecto():
    datos = seccion_datos_proyecto()
    if datos:
        st.session_state["datos_proyecto"] = datos


def renderizar_cables():
    cables = seccion_cables()
    if cables is not None:
        st.session_state["cables"] = cables


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

    if "modo_carga_seleccionado" not in st.session_state:
        st.warning("⚠️ Primero selecciona el modo de carga.")
        return

    modo = st.session_state["modo_carga_seleccionado"]

    if modo != "manual":
        st.info("⚠️ Por ahora solo está activo modo desplegables.")
        return

    # =====================================================
    # 🔥 LLAMAR UI REAL (ESTO FALTABA)
    # =====================================================
    df, ruta = seccion_entrada_estructuras()

    if df is None:
        st.info("⚠️ No hay estructuras aún.")
        return

    # =====================================================
    # GUARDAR RESULTADO GLOBAL
    # =====================================================
    st.session_state["df_estructuras"] = df
    st.session_state["ruta_estructuras_compacto"] = ruta

    st.success("✅ Estructuras listas.")

def renderizar_final():

    df = st.session_state.get("df_estructuras")

    if not es_dataframe_valido(df):
        st.warning("⚠️ Carga estructuras primero.")
        return

    # Validación mínima
    if df is None or df.empty:
        st.error("❌ Estructuras inválidas.")
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


# =========================================================
# ORQUESTADOR PRINCIPAL
# =========================================================

def ejecutar_orquestador_interfaz(
    _nav_estado_actual,
    _barra_nav_botones,
):

    # =====================================================
    # INICIALIZACIÓN SEGURA
    # =====================================================
    st.session_state.setdefault("df_estructuras", None)
    st.session_state.setdefault("ruta_estructuras_compacto", None)
    st.session_state.setdefault("modo_carga_seleccionado", None)

    # =====================================================
    # NAVEGACIÓN
    # =====================================================
    seccion = _nav_estado_actual()

    _barra_nav_botones(seccion)

    # =====================================================
    # MAPA DE SECCIONES
    # =====================================================
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
