# -*- coding: utf-8 -*-
# ayuda/debug.py

import streamlit as st


# =========================================================
# GUARDAR DEBUG GLOBAL
# =========================================================
def debug_guardar(clave: str, valor):

    if "debug_extra" not in st.session_state:
        st.session_state["debug_extra"] = {}

    st.session_state["debug_extra"][clave] = valor


# =========================================================
# GRAFO DE ESTRUCTURAS
# =========================================================
def _grafo_estructuras(df):

    if df is None or df.empty:
        st.info("No hay estructuras para graficar")
        return

    try:
        import graphviz

        dot = graphviz.Digraph()

        # Nodo raíz
        dot.node("Proyecto", shape="box")

        for _, row in df.iterrows():

            punto = str(row.get("Punto"))
            estructura = str(row.get("Estructura"))

            nodo_punto = f"P_{punto}"
            nodo_est = f"{punto}_{estructura}"

            # Nodo punto
            dot.node(nodo_punto, f"Punto {punto}", shape="circle")

            # Nodo estructura
            dot.node(nodo_est, estructura, shape="box")

            # Conexiones
            dot.edge("Proyecto", nodo_punto)
            dot.edge(nodo_punto, nodo_est)

        st.graphviz_chart(dot)

    except Exception as e:
        st.error(f"Error generando grafo: {e}")


# =========================================================
# UI DEBUG
# =========================================================
def seccion_debug():

    st.subheader("🧠 Debug del sistema")

    debug = st.session_state.get("debug_pipeline")

    if not debug:
        st.info("No hay información de debug aún")
    else:
        st.markdown("### 📊 Estado del Pipeline")
        st.json(debug)

    # =====================================================
    # GRAFO 🔥
    # =====================================================
    st.markdown("### 🧭 Grafo del proyecto")

    df = st.session_state.get("df_estructuras")
    _grafo_estructuras(df)

    # =====================================================
    # DEBUG EXTRA
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
