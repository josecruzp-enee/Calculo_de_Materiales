# -*- coding: utf-8 -*-
# ayuda/debug.py

import streamlit as st


def seccion_debug():

    st.subheader("🧠 Debug del sistema")

    debug = st.session_state.get("debug_pipeline")

    if not debug:
        st.info("No hay información de debug aún")
        return

    st.markdown("### 📊 Estado del Pipeline")

    st.json(debug)

    # =========================
    # DEBUG COMPLETO
    # =========================
    with st.expander("🔍 Ver session_state completo"):

        for k, v in st.session_state.items():
            st.write(f"**{k}**:", v)
