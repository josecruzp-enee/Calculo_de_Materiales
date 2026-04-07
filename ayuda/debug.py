# -*- coding: utf-8 -*-
# ayuda/debug.py

from __future__ import annotations
import streamlit as st
import pandas as pd


# =========================================================
# 🔷 GUARDAR DEBUG GLOBAL (UNIFICADO)
# =========================================================
def debug_guardar(clave: str, valor):

    if "debug_pipeline" not in st.session_state:
        st.session_state["debug_pipeline"] = {}

    st.session_state["debug_pipeline"][clave] = valor


# =========================================================
# 🔷 ESTADO VISUAL
# =========================================================
def _estado(ok):
    return "🟢" if ok else "🔴"


# =========================================================
# 🔷 PIPELINE REAL (RUNTIME)
# =========================================================
def _pipeline_runtime():

    df = st.session_state.get("df_estructuras")
    resultado = st.session_state.get("resultado_calculo")

    pasos = []

    pasos.append(("UI", True))

    pasos.append((
        "Entradas",
        isinstance(df, pd.DataFrame) and not df.empty
    ))

    pasos.append((
        "Normalización",
        isinstance(df, pd.DataFrame)
        and "Estructura" in df.columns
        and df["Estructura"].notna().any()
    ))

    pasos.append((
        "Materiales",
        resultado is not None
        and hasattr(resultado, "df_materiales")
    ))

    pasos.append((
        "Exportación",
        resultado is not None
    ))

    pasos.append((
        "PDF",
        resultado is not None
    ))

    return pasos


# =========================================================
# 🔷 RENDER PIPELINE
# =========================================================
def _render_pipeline_runtime():

    st.markdown("### 🧠 Pipeline en tiempo real")

    pasos = _pipeline_runtime()

    for nombre, ok in pasos:

        icono = "🟢" if ok else "🔴"
        st.write(f"{icono} {nombre}")

        if not ok:
            st.error(f"⚠️ Falla en: {nombre}")
            break


# =========================================================
# 🔷 GRAFO PIPELINE (VISUAL)
# =========================================================
def _grafo_pipeline():

    pasos = _pipeline_runtime()

    st.markdown("### 🔄 Flujo del sistema")

    try:
        import graphviz

        dot = graphviz.Digraph()

        prev = None

        for nombre, ok in pasos:

            estado = "🟢" if ok else "🔴"
            label = f"{nombre}\n{estado}"

            dot.node(nombre, label)

            if prev:
                dot.edge(prev, nombre)

            prev = nombre

        st.graphviz_chart(dot)

    except Exception:
        for nombre, ok in pasos:
            estado = "🟢" if ok else "🔴"
            st.write(f"{estado} {nombre}")


# =========================================================
# 🔷 RENDER DE BLOQUE DEBUG
# =========================================================
def _render_valor_debug(valor):

    if isinstance(valor, pd.DataFrame):
        st.caption(f"Filas: {len(valor)} | Columnas: {list(valor.columns)}")
        st.dataframe(valor.head(10), use_container_width=True)

    elif isinstance(valor, dict):
        st.json(valor)

    elif hasattr(valor, "__dict__"):
        st.json(valor.__dict__)

    else:
        st.write(valor)


# =========================================================
# 🔷 AUDITORÍA REAL DE ESTRUCTURAS (CRÍTICO)
# =========================================================
def _auditar_estructuras():

    st.markdown("### 🔍 Auditoría de estructuras")

    df = st.session_state.get("df_estructuras")

    if df is None:
        st.error("df_estructuras = None")
        return

    if not isinstance(df, pd.DataFrame):
        st.error(f"df_estructuras no es DataFrame: {type(df)}")
        return

    st.write("Shape:", df.shape)
    st.write("Columnas:", list(df.columns))

    st.write("Primeras filas:")
    st.dataframe(df.head(10), use_container_width=True)

    if "Estructura" in df.columns:
        st.write("Valores únicos (Estructura):")
        st.write(sorted(df["Estructura"].dropna().unique())[:20])
    else:
        st.warning("⚠️ No existe columna 'Estructura'")

def _debug_critico_materiales():

    st.markdown("### 🚨 Diagnóstico REAL del problema")

    df = st.session_state.get("df_estructuras")
    resultado = st.session_state.get("resultado_calculo")
    hojas = st.session_state.get("hojas_base")

    if df is None or df.empty:
        st.error("No hay estructuras cargadas")
        return

    if hojas is None:
        st.error("No se cargó base de datos (Estructura_datos.xlsx)")
        return

    estructuras_input = set(df["Estructura"].dropna().unique())
    estructuras_base = set(hojas.keys())

    # =========================================
    # 1. ESTRUCTURAS NO EXISTEN EN BASE
    # =========================================
    no_existen = estructuras_input - estructuras_base

    if no_existen:
        st.error("❌ Estructuras no encontradas en base:")
        st.write(sorted(no_existen))

    else:
        st.success("✔ Todas las estructuras existen en la base")

    # =========================================
    # 2. HOJAS VACÍAS
    # =========================================
    vacias = []

    for est in estructuras_input:
        df_est = hojas.get(est)
        if df_est is None or df_est.empty:
            vacias.append(est)

    if vacias:
        st.error("❌ Estructuras sin materiales:")
        st.write(vacias)

    # =========================================
    # 3. VALIDAR TENSIÓN
    # =========================================
    tension = st.session_state.get("tension")

    columnas_invalidas = []

    for est in estructuras_input:
        df_est = hojas.get(est)
        if df_est is not None and tension not in df_est.columns:
            columnas_invalidas.append(est)

    if columnas_invalidas:
        st.error(f"❌ No tienen columna de tensión {tension}:")
        st.write(columnas_invalidas)

    # =========================================
    # 4. RESULTADO VACÍO
    # =========================================
    if resultado and hasattr(resultado, "df_materiales"):
        if resultado.df_materiales.empty:
            st.error("❌ Se calcularon materiales pero el resultado está vacío")



# =========================================================
# 🔷 UI DEBUG PRINCIPAL
# =========================================================
def seccion_debug():

    st.title("🧠 Debug del sistema")

    # =====================================================
    # DEBUG GLOBAL
    # =====================================================
    debug = st.session_state.get("debug_pipeline")

    if debug:
        st.markdown("### 📊 Estado del Pipeline")

        for clave, valor in debug.items():
            st.markdown(f"#### 🔹 {clave}")
            _render_valor_debug(valor)

    else:
        st.info("No hay información de debug aún")

    # =====================================================
    # 🔴 AUDITORÍA REAL
    # =====================================================
    _auditar_estructuras()
    _debug_critico_materiales()
    # =====================================================
    # 🔥 PIPELINE REAL
    # =====================================================
    _render_pipeline_runtime()

    # =====================================================
    # 🔄 GRAFO
    # =====================================================
    _grafo_pipeline()

    # =====================================================
    # SESSION COMPLETA
    # =====================================================
    with st.expander("🔍 Ver session_state completo"):
        for k, v in st.session_state.items():
            st.write(f"**{k}**:", v)
