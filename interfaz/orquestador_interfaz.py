# -*- coding: utf-8 -*-
from __future__ import annotations

import streamlit as st
import pandas as pd  # 🔥 necesario para tablas

# =========================================================
# CONTRATOS
# =========================================================
from interfaz.contratos import SalidaInterfaz

# =========================================================
# ORQUESTADOR APP
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
        "cables_proyecto_df": pd.DataFrame(),
        "df_materiales_extra": None,
        "resultado_calculo": None,
        "ejecutar_proyecto_flag": False,
        "debug_pipeline": {},
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# =========================================================
# UI SECCIONES
# =========================================================
def renderizar_datos_proyecto():
    datos = seccion_datos_proyecto()
    if datos:
        st.session_state["datos_proyecto"] = datos


def renderizar_cables():
    cables = seccion_cables()

    if cables and cables.get("ok"):
        df = cables.get("df")

        if isinstance(df, pd.DataFrame):
            st.session_state["cables_proyecto_df"] = df.copy()
            st.session_state["cables_proyecto"] = cables.get("cables", [])

def renderizar_modo_carga():
    seleccionar_modo_carga()


def renderizar_estructuras():
    modo = st.session_state.get("modo_carga_seleccionado")

    if not modo:
        st.warning("⚠️ Primero selecciona modo de carga.")
        return

    st.session_state["tipo_entrada"] = modo

    data = None

    if modo == "manual":
        df, _ = seccion_entrada_estructuras()

        if df is None or df.empty:
            return

        st.session_state["data_entrada"] = df
        st.session_state["resultado_calculo"] = None

        st.success("✅ Datos ingresados correctamente")
        st.info("➡️ Ahora puedes ir a 'Finalizar'")

    elif modo == "excel":
        data = st.file_uploader("Subir Excel", type=["xlsx"])

    elif modo == "tabla":
        data = st.text_area("Pegar tabla")

    elif modo == "pdf":
        data = st.file_uploader("Subir PDF", type=["pdf"])

    elif modo == "dxf":
        data = st.file_uploader("Subir DXF", type=["dxf"])

    if data is not None and modo != "manual":
        st.session_state["data_entrada"] = data
        st.session_state["resultado_calculo"] = None

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

    if st.button("🚀 Ejecutar proyecto"):
        st.session_state["ejecutar_proyecto_flag"] = True
        st.rerun()

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
# CONTRATO INTERFAZ
# =========================================================
def _construir_salida_interfaz() -> SalidaInterfaz:

    errores = []
    warnings = []

    tipo = st.session_state.get("tipo_entrada")
    data = st.session_state.get("data_entrada")
    datos = st.session_state.get("datos_proyecto") or {}
    df_tmp = st.session_state.get("cables_proyecto_df")
    df_cables = df_tmp if isinstance(df_tmp, pd.DataFrame) else None
    
    if not tipo:
        errores.append("Modo de entrada no seleccionado")

    if data is None:
        errores.append("No se proporcionó entrada")

    salida = SalidaInterfaz(
        ok=len(errores) == 0,
        errores=errores,
        warnings=warnings,
        tipo_entrada=tipo or "manual",
        data_entrada=data,
        datos_proyecto=datos,
        df_cables=df_cables,
        df_materiales_extra=st.session_state.get("df_materiales_extra"),
     
    )

    # DEBUG INTERFAZ (se mantiene igual)
    salida.debug = {
        "input": {
            "tipo_entrada": salida.tipo_entrada,
            "tiene_data": salida.data_entrada is not None,
            "tipo_data": str(type(salida.data_entrada)),
            "datos_proyecto_keys": list(datos.keys()),
        },
        "output": {
            "ok": salida.ok,
            "errores": salida.errores,
            "warnings": salida.warnings,
        }
    }

    return salida


# =========================================================
# ORQUESTADOR UI
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

    salida_interfaz = _construir_salida_interfaz()
    resultado = st.session_state.get("resultado_calculo")

    # =========================================================
    # DEBUG PIPELINE
    # =========================================================
    debug_actual = {
        "INTERFAZ": salida_interfaz.debug
    }

    if resultado:
        debug_actual["PROYECTO"] = {
            "ok": resultado.ok,
            "errores": resultado.errores,
            "warnings": resultado.warnings,
        }

        if hasattr(resultado, "debug") and isinstance(resultado.debug, dict):
            debug_actual.update(resultado.debug)

    st.session_state["debug_pipeline"] = debug_actual

    # =========================================================
    # 🔥 DEBUG VISUAL EN TABLAS
    # =========================================================
    st.markdown("## 🧠 Debug del sistema")

    for bloque, contenido in debug_actual.items():

        st.markdown(f"### 🔹 {bloque}")

        if isinstance(contenido, dict):

            for k, v in contenido.items():

                st.markdown(f"#### {k}")

                if isinstance(v, pd.DataFrame):
                    st.dataframe(v)

                elif isinstance(v, dict):
                    try:
                        df = pd.DataFrame(v)
                        st.dataframe(df)
                    except:
                        st.write(v)

                else:
                    st.write(v)

        elif isinstance(contenido, pd.DataFrame):
            st.dataframe(contenido)

        else:
            st.write(contenido)

    # =========================================================
    # 🔍 AUDITORÍA CLAVE
    # =========================================================
    st.markdown("## 🔍 Auditoría de estructuras")

    try:
        df_test = resultado.materiales.df_estructuras
    except:
        df_test = None

    st.write("df_estructuras =", df_test)

    return resultado
