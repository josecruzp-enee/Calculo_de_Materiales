# -*- coding: utf-8 -*-
# interfaz/orquestador_interfaz.py

from __future__ import annotations

import streamlit as st

# =========================================================
# CONTRATO
# =========================================================
from interfaz.contratos import SalidaInterfaz

# =========================================================
# IMPORTS UI
# =========================================================
from interfaz.base import seleccionar_modo_carga

from interfaz.datos_proyecto import seccion_datos_proyecto
from interfaz.cables_ui import seccion_cables
from interfaz.estructuras_ui import seccion_entrada_estructuras

from interfaz.exportacion_ui import (
    seccion_finalizar_calculo,
    seccion_exportacion,
)

try:
    from interfaz.materiales_extra import obtener_materiales_finales
except Exception:
    def obtener_materiales_finales():
        return None

from ayuda.debug import seccion_debug


# =========================================================
# HELPERS
# =========================================================
def es_dataframe_valido(df):
    return df is not None and hasattr(df, "empty") and not df.empty


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
# DEBUG
# =========================================================
def _resumen_df(df):
    if df is None:
        return None
    if hasattr(df, "shape"):
        return {
            "filas": df.shape[0],
            "columnas": list(df.columns)
        }
    return str(type(df))


def _actualizar_debug_pipeline():

    st.session_state["debug_pipeline"] = {
        "modo": st.session_state.get("modo_carga_seleccionado"),
        "tipo_entrada": st.session_state.get("tipo_entrada"),
        "data_entrada_tipo": type(st.session_state.get("data_entrada")).__name__,

        "df_estructuras": _resumen_df(st.session_state.get("df_estructuras")),
        "cables": _resumen_df(st.session_state.get("cables_proyecto_df")),
        "datos_proyecto": st.session_state.get("datos_proyecto"),
        "materiales_extra": _resumen_df(st.session_state.get("df_materiales_extra")),

        # 🔥 contrato
        "contrato_interfaz": {
            "tipo_entrada": st.session_state.get("tipo_entrada"),
            "data_valida": st.session_state.get("data_entrada") is not None,
        }
    }


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
# ESTRUCTURAS
# =========================================================
def renderizar_estructuras():

    modo = st.session_state.get("modo_carga_seleccionado")

    if not modo:
        st.warning("⚠️ Primero selecciona el modo de carga.")
        return

    archivo = None
    df_ui = None

    try:

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

        else:
            st.warning(f"Modo no soportado: {modo}")
            return

    except Exception as e:
        st.error(f"Error en carga: {e}")
        return

    st.session_state["tipo_entrada"] = modo

    if df_ui is not None:
        st.session_state["data_entrada"] = df_ui
    else:
        st.session_state["data_entrada"] = archivo

    st.success(f"Entrada cargada correctamente ({modo})")


# =========================================================
# FINAL
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
# 🔥 CONSTRUCTOR DE SALIDA
# =========================================================
def _construir_salida() -> SalidaInterfaz:

    errores = []
    warnings = []

    tipo_entrada = st.session_state.get("tipo_entrada")
    data_entrada = st.session_state.get("data_entrada")

    if not tipo_entrada:
        errores.append("Modo de entrada no seleccionado")

    if data_entrada is None:
        errores.append("No hay datos de entrada")

    return SalidaInterfaz(
        ok=len(errores) == 0,
        errores=errores,
        warnings=warnings,
        tipo_entrada=tipo_entrada or "manual",
        data_entrada=data_entrada,
        datos_proyecto=st.session_state.get("datos_proyecto") or {},
        df_cables=st.session_state.get("cables_proyecto_df"),
        df_materiales_extra=st.session_state.get("df_materiales_extra"),
        debug=st.session_state.get("debug_pipeline") or {},
    )


# =========================================================
# ORQUESTADOR PRINCIPAL
# =========================================================
def ejecutar_orquestador_interfaz(
    _nav_estado_actual,
    _barra_nav_botones,
) -> SalidaInterfaz:

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
        "debug": seccion_debug,
    }

    funcion = acciones.get(seccion)

    if funcion:
        funcion()
    else:
        st.warning("Sección no reconocida.")

    _actualizar_debug_pipeline()

    return _construir_salida()
