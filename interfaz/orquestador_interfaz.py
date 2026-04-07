# -*- coding: utf-8 -*-
# interfaz/orquestador_interfaz.py

from __future__ import annotations
import streamlit as st

# =========================================================
# CONTRATOS
# =========================================================
from interfaz.contratos import SalidaInterfaz
from entradas.orquestador_entradas import ejecutar_entradas

# =========================================================
# UI
# =========================================================
from interfaz.base import seleccionar_modo_carga
from interfaz.datos_proyecto import seccion_datos_proyecto
from interfaz.cables_ui import seccion_cables
from interfaz.estructuras_ui import seccion_entrada_estructuras

from interfaz.exportacion_ui import (
    seccion_finalizar_calculo,
    seccion_exportacion,
)

from ayuda.debug import seccion_debug


# =========================================================
# STATE
# =========================================================
def _init_state():
    defaults = {
        "df_estructuras": None,
        "modo_carga_seleccionado": None,
        "cables_proyecto_df": None,
        "datos_proyecto": None,
        "df_materiales_extra": None,
        "tipo_entrada": None,
        "data_entrada": None,
        "debug_pipeline": {},
    }

    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


# =========================================================
# UI SECCIONES
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
        st.warning("⚠️ Primero selecciona modo.")
        return

    archivo = None
    df_ui = None

    if modo == "manual":
        df, _ = seccion_entrada_estructuras()
        if df is None or df.empty:
            return
        df_ui = df

    elif modo == "excel":
        archivo = st.file_uploader("Subir Excel", type=["xlsx"])

    elif modo == "tabla":
        archivo = st.text_area("Pegar tabla")

    elif modo == "pdf":
        archivo = st.file_uploader("Subir PDF", type=["pdf"])

    elif modo == "dxf":
        archivo = st.file_uploader("Subir DXF", type=["dxf"])

    st.session_state["tipo_entrada"] = modo
    st.session_state["data_entrada"] = df_ui if df_ui is not None else archivo


def renderizar_final():
    if st.session_state.get("df_estructuras") is None:
        st.warning("Carga estructuras primero")
        return
    seccion_finalizar_calculo()


def renderizar_exportacion():
    if st.session_state.get("df_estructuras") is None:
        st.warning("Carga estructuras primero")
        return
    seccion_exportacion()


# =========================================================
# CONTRATO INTERFAZ
# =========================================================
def _construir_salida() -> SalidaInterfaz:

    errores = []

    tipo = st.session_state.get("tipo_entrada")
    data = st.session_state.get("data_entrada")

    if not tipo:
        errores.append("Modo no seleccionado")

    if data is None:
        errores.append("No hay datos")

    return SalidaInterfaz(
        ok=len(errores) == 0,
        errores=errores,
        warnings=[],
        tipo_entrada=tipo or "manual",
        data_entrada=data,
        datos_proyecto=st.session_state.get("datos_proyecto") or {},
        df_cables=st.session_state.get("cables_proyecto_df"),
        df_materiales_extra=st.session_state.get("df_materiales_extra"),
        debug={}
    )


# =========================================================
# ORQUESTADOR
# =========================================================
def ejecutar_orquestador_interfaz(
    _nav_estado_actual,
    _barra_nav_botones,
):

    _init_state()

    sec = _nav_estado_actual()
    _barra_nav_botones(sec)

    acciones = {
        "datos": renderizar_datos_proyecto,
        "cables": renderizar_cables,
        "modo": renderizar_modo_carga,
        "estructuras": renderizar_estructuras,
        "final": renderizar_final,
        "exportar": renderizar_exportacion,
        "debug": seccion_debug,
    }

    if sec in acciones:
        acciones[sec]()

    # =====================================================
    # 🔥 INTERFAZ → ENTRADAS
    # =====================================================
    salida_interfaz = _construir_salida()

    salida_entradas = ejecutar_entradas(
        salida_interfaz,
        tension=13.8,
    )

    # persistencia para UI
    if salida_entradas.ok:
        st.session_state["df_estructuras"] = salida_entradas.df_estructuras

    return salida_entradas
