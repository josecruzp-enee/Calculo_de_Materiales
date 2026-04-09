# -*- coding: utf-8 -*-
from __future__ import annotations

import streamlit as st

# =========================================================
# CONTRATOS
# =========================================================
from interfaz.contratos import SalidaInterfaz

# =========================================================
# ORQUESTADOR ÚNICO
# =========================================================
from aplicacion.orquestador_proyecto import ejecutar_proyecto

# =========================================================
# UI
# =========================================================
from interfaz.base import seleccionar_modo_carga
from interfaz.datos_proyecto import seccion_datos_proyecto
from interfaz.cables_ui import seccion_cables
from interfaz.estructuras_ui import seccion_entrada_estructuras
from interfaz.exportacion_ui import seccion_exportacion
from ayuda.debug import seccion_debug


# =========================================================
# STATE
# =========================================================
def _init_state():
    defaults = {
        "modo_carga_seleccionado": None,
        "tipo_entrada": None,
        "data_entrada": None,
        "datos_proyecto": {},
        "cables_proyecto_df": None,
        "df_materiales_extra": None,
        "resultado_calculo": None,
        "ejecutar_proyecto_flag": False,
        "debug_pipeline": {},
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


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
    seleccionar_modo_carga()


def renderizar_estructuras():
    modo = st.session_state.get("modo_carga_seleccionado")

    if not modo:
        st.warning("⚠️ Primero selecciona modo de carga.")
        return

    # 🔥 sincronización contrato
    st.session_state["tipo_entrada"] = modo

    data = None

    # =====================================================
    # MANUAL
    # =====================================================
    if modo == "manual":
        df, _ = seccion_entrada_estructuras()

        if df is None or df.empty:
            return

        st.session_state["data_entrada"] = df
        st.session_state["resultado_calculo"] = None  # 🔥 limpiar resultado

        st.success("✅ Datos ingresados correctamente")
        st.info("➡️ Ahora puedes ir a 'Finalizar'")

    # =====================================================
    # ARCHIVOS
    # =====================================================
    elif modo == "excel":
        data = st.file_uploader("Subir Excel", type=["xlsx"])

    elif modo == "tabla":
        data = st.text_area("Pegar tabla")

    elif modo == "pdf":
        data = st.file_uploader("Subir PDF", type=["pdf"])

    elif modo == "dxf":
        data = st.file_uploader("Subir DXF", type=["dxf"])

    # =====================================================
    # MANEJO GENERAL
    # =====================================================
    if data is not None and modo != "manual":
        st.session_state["data_entrada"] = data
        st.session_state["resultado_calculo"] = None  # 🔥 limpiar resultado

        if hasattr(data, "name"):
            st.success(f"✅ Archivo cargado: {data.name}")
        else:
            st.success("✅ Datos cargados correctamente")

        st.info("➡️ Ahora puedes ir a 'Finalizar'")


def renderizar_final():
    st.subheader("⚙️ Finalizar cálculo")

    salida_interfaz = _construir_salida_interfaz()

    if not salida_interfaz.ok:
        st.error("❌ Datos incompletos")
        for e in salida_interfaz.errores:
            st.error(f"• {e}")
        return

    # =====================================================
    # BOTÓN DE EJECUCIÓN
    # =====================================================
    if st.button("🚀 Ejecutar proyecto"):
        st.session_state["ejecutar_proyecto_flag"] = True
        st.rerun()

    # =====================================================
    # EJECUCIÓN CONTROLADA
    # =====================================================
    if st.session_state.get("ejecutar_proyecto_flag"):

        with st.spinner("Ejecutando proyecto completo..."):
            resultado = ejecutar_proyecto(salida_interfaz)

        st.session_state["resultado_calculo"] = resultado
        st.session_state["ejecutar_proyecto_flag"] = False

        if resultado and resultado.ok:
            st.success("✅ Proyecto ejecutado correctamente")
        else:
            st.error("❌ Error en ejecución")


def renderizar_exportacion():
    resultado = st.session_state.get("resultado_calculo")

    if resultado is None or not getattr(resultado, "ok", False):
        st.warning("⚠️ Debes ejecutar el cálculo primero.")
        return

    seccion_exportacion()


# =========================================================
# CONSTRUCCIÓN DE CONTRATO
# =========================================================
def _construir_salida_interfaz() -> SalidaInterfaz:

    errores = []
    warnings = []

    tipo = st.session_state.get("tipo_entrada")
    data = st.session_state.get("data_entrada")

    if not tipo:
        errores.append("Modo de entrada no seleccionado")

    if data is None:
        errores.append("No se proporcionó entrada")

    return SalidaInterfaz(
        ok=len(errores) == 0,
        errores=errores,
        warnings=warnings,
        tipo_entrada=tipo or "manual",
        data_entrada=data,
        datos_proyecto=st.session_state.get("datos_proyecto") or {},
        df_cables=st.session_state.get("cables_proyecto_df"),
        df_materiales_extra=st.session_state.get("df_materiales_extra"),
        debug={
            "tipo": tipo,
            "tiene_data": data is not None,
        }
    )


# =========================================================
# ORQUESTADOR PRINCIPAL UI
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
    # DEBUG PIPELINE
    # =====================================================
    salida_interfaz = _construir_salida_interfaz()
    resultado = st.session_state.get("resultado_calculo")

    debug_actual = {
        "INTERFAZ": {
            "ok": salida_interfaz.ok,
            "errores": salida_interfaz.errores,
            "tipo_entrada": salida_interfaz.tipo_entrada,
            "tiene_data": salida_interfaz.data_entrada is not None,
        }
    }

    if resultado:
        debug_actual["RESULTADO_PROYECTO"] = {
            "ok": resultado.ok,
            "errores": resultado.errores,
            "warnings": resultado.warnings,
        }

    st.session_state["debug_pipeline"] = debug_actual

    return resultado
