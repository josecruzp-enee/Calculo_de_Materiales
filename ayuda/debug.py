# -*- coding: utf-8 -*-
# ayuda/debug.py

import streamlit as st


# =========================================================
# GUARDAR DEBUG DESDE CUALQUIER PARTE DEL SISTEMA
# =========================================================
def debug_guardar(clave: str, valor):

    if "debug_extra" not in st.session_state:
        st.session_state["debug_extra"] = {}

    st.session_state["debug_extra"][clave] = valor


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

    # =========================
    # DEBUG EXTRA (🔥 IMPORTANTE)
    # =========================
    debug_extra = st.session_state.get("debug_extra")

    if debug_extra:
        st.markdown("### 🧪 Debug interno")
        st.json(debug_extra)

    # =========================
    # SESSION COMPLETA
    # =========================
    with st.expander("🔍 Ver session_state completo"):
        for k, v in st.session_state.items():
            st.write(f"**{k}**:", v)
