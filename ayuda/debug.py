# -*- coding: utf-8 -*-
# ayuda/debug.py

from __future__ import annotations
import streamlit as st
import pandas as pd


# =========================================================
# 🔷 GUARDAR DEBUG GLOBAL (UNIFICADO)
# =========================================================
def debug_guardar(clave: str, valor):
    """
    Guarda información de debug accesible desde cualquier capa.
    """

    if "debug_pipeline" not in st.session_state:
        st.session_state["debug_pipeline"] = {}

    st.session_state["debug_pipeline"][clave] = valor


# =========================================================
# 🔷 ESTADO VISUAL
# =========================================================
def _estado(ok):
    return "🟢" if ok else "🔴"


# =========================================================
# 🔷 EVALUAR ESTADO REAL DEL SISTEMA
# =========================================================
def _evaluar_pipeline():

    df = st.session_state.get("df_estructuras")
    resultado = st.session_state.get("resultado_calculo")

    estados = {
        "UI": True,
        "Entradas": isinstance(df, pd.DataFrame) and not df.empty,
        "Normalización": isinstance(df, pd.DataFrame) and "Punto" in df.columns,
        "Materiales": resultado is not None,
        "Exportación": resultado is not None,
        "PDF": resultado is not None,
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

        # Nodos
        dot.node("UI", f"UI\n{_estado(estados['UI'])}")
        dot.node("ENT", f"Entradas\n{_estado(estados['Entradas'])}")
        dot.node("NOR", f"Normalización\n{_estado(estados['Normalización'])}")
        dot.node("MAT", f"Materiales\n{_estado(estados['Materiales'])}")
        dot.node("EXP", f"Exportación\n{_estado(estados['Exportación'])}")
        dot.node("PDF", f"PDF\n{_estado(estados['PDF'])}")

        # Flujo
        dot.edge("UI", "ENT")
        dot.edge("ENT", "NOR")
        dot.edge("NOR", "MAT")
        dot.edge("MAT", "EXP")
        dot.edge("EXP", "PDF")

        st.graphviz_chart(dot)

    except Exception:
        # fallback simple
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

    # DataFrame
    if isinstance(valor, pd.DataFrame):
        st.caption(f"Filas: {len(valor)} | Columnas: {list(valor.columns)}")
        st.dataframe(valor.head(10), use_container_width=True)

    # Diccionario
    elif isinstance(valor, dict):
        st.json(valor)

    # Objetos tipo dataclass
    elif hasattr(valor, "__dict__"):
        st.json(valor.__dict__)

    # Otros
    else:
        st.write(valor)


# =========================================================
# 🔷 UI DEBUG PRINCIPAL
# =========================================================
def seccion_debug():

    st.title("🧠 Debug del sistema")

    # =====================================================
    # ESTADO DEL PIPELINE
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
    # GRAFO DEL SISTEMA
    # =====================================================
    estados = _evaluar_pipeline()
    _grafo_pipeline(estados)

    # =====================================================
    # SESSION COMPLETA
    # =====================================================
    with st.expander("🔍 Ver session_state completo"):
        for k, v in st.session_state.items():
            st.write(f"**{k}**:", v)
