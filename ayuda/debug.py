# -*- coding: utf-8 -*-
# ayuda/debug.py

import streamlit as st


# =========================================================
# GUARDAR DEBUG GLOBAL (para usar en cualquier módulo)
# =========================================================
def debug_guardar(clave: str, valor):

    if "debug_extra" not in st.session_state:
        st.session_state["debug_extra"] = {}

    st.session_state["debug_extra"][clave] = valor


# =========================================================
# ESTADO VISUAL
# =========================================================
def _estado(ok):
    return "🟢" if ok else "🔴"


# =========================================================
# EVALUAR ESTADO REAL DEL SISTEMA
# =========================================================
def _evaluar_pipeline():

    df = st.session_state.get("df_estructuras")
    resultado = st.session_state.get("resultado_calculo")
    datos = st.session_state.get("datos_proyecto")

    estados = {
        "UI": True,
        "Entradas": df is not None and hasattr(df, "empty") and not df.empty,
        "Normalización": df is not None and hasattr(df, "columns") and "Punto" in df.columns,
        "Materiales": resultado is not None,
        "Exportación": resultado is not None,
        "PDF": resultado is not None,
    }

    return estados


# =========================================================
# GRAFO PIPELINE
# =========================================================
def _grafo_pipeline(estados):

    st.markdown("### 🔄 Flujo del sistema")

    try:
        import graphviz

        dot = graphviz.Digraph()

        # Nodos con estado
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
        # Fallback si no hay graphviz
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
# UI DEBUG
# =========================================================
def seccion_debug():

    st.title("🧠 Debug del sistema")

    # =====================================================
    # ESTADO DEL PIPELINE
    # =====================================================
    debug = st.session_state.get("debug_pipeline")

    if debug:
        st.markdown("### 📊 Estado del Pipeline")
        st.json(debug)
    else:
        st.info("No hay información de debug aún")

    # =====================================================
    # GRAFO DEL SISTEMA 🔥
    # =====================================================
    estados = _evaluar_pipeline()
    _grafo_pipeline(estados)

    # =====================================================
    # DEBUG INTERNO
    # =====================================================
    debug_extra = st.session_state.get("debug_extra")

    if debug_extra:
        st.markdown("### 🧪 Debug interno")
        st.json(debug_extra)

    # =====================================================
    # SESSION COMPLETA
    # =====================================================
    with st.expander("🔍 Ver session_state completo"):
        for k, v in st.session_state.items():
            st.write(f"**{k}**:", v)
