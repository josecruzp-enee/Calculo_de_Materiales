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
# 🔷 EVALUAR ESTADO REAL DEL SISTEMA (CORREGIDO)
# =========================================================
def _evaluar_pipeline():

    df = st.session_state.get("df_estructuras")
    resultado = st.session_state.get("resultado_calculo")

    # =========================
    # VALIDACIONES REALES
    # =========================
    entradas_ok = isinstance(df, pd.DataFrame) and not df.empty

    normalizacion_ok = (
        entradas_ok
        and "Punto" in df.columns
        and "Estructura" in df.columns
        and df["Estructura"].notna().any()
    )

    materiales_ok = (
        resultado is not None
        and hasattr(resultado, "df_materiales")
        and isinstance(resultado.df_materiales, pd.DataFrame)
        and not resultado.df_materiales.empty
    )

    estados = {
        "UI": True,
        "Entradas": entradas_ok,
        "Normalización": normalizacion_ok,
        "Materiales": materiales_ok,
        "Exportación": materiales_ok,
        "PDF": materiales_ok,
    }

    return estados


# =========================================================
# 🔷 GRAFO PIPELINE
# =========================================================
def _grafo_pipeline(estados):

    st.markdown("### 🔄 Flujo del sistema")

    try:
        import graphviz

        dot = graphviz.Digraph()

        dot.node("UI", f"UI\n{_estado(estados['UI'])}")
        dot.node("ENT", f"Entradas\n{_estado(estados['Entradas'])}")
        dot.node("NOR", f"Normalización\n{_estado(estados['Normalización'])}")
        dot.node("MAT", f"Materiales\n{_estado(estados['Materiales'])}")
        dot.node("EXP", f"Exportación\n{_estado(estados['Exportación'])}")
        dot.node("PDF", f"PDF\n{_estado(estados['PDF'])}")

        dot.edge("UI", "ENT")
        dot.edge("ENT", "NOR")
        dot.edge("NOR", "MAT")
        dot.edge("MAT", "EXP")
        dot.edge("EXP", "PDF")

        st.graphviz_chart(dot)

    except Exception:
        st.markdown(f"""
        UI {_estado(estados['UI'])}  
        ↓  
        Entradas {_estado(estados['Entradas'])}  
        ↓  
        Normalización {_estado(estados['Normalización'])}  
        ↓  
        Materiales {_estado(estados['Materiales'])}  
        ↓  
        Exportación {_estado(estados['Exportación'])}  
        ↓  
        PDF {_estado(estados['PDF'])}
        """)


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
# 🔷 AUDITORÍA REAL DE ESTRUCTURAS (NUEVO 🔥)
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

    # Validación crítica
    if "Estructura" in df.columns:
        st.write("Valores únicos (Estructura):")
        st.write(sorted(df["Estructura"].dropna().unique())[:20])
    else:
        st.warning("No existe columna 'Estructura'")


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
    # 🔴 AUDITORÍA REAL (CLAVE)
    # =====================================================
    _auditar_estructuras()

    # =====================================================
    # GRAFO
    # =====================================================
    estados = _evaluar_pipeline()
    _grafo_pipeline(estados)

    # =====================================================
    # SESSION COMPLETA
    # =====================================================
    with st.expander("🔍 Ver session_state completo"):
        for k, v in st.session_state.items():
            st.write(f"**{k}**:", v)
