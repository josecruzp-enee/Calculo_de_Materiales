# -*- coding: utf-8 -*-
import streamlit as st


def seccion_debug():

    st.subheader("🧠 Debug del sistema")

    debug_data = st.session_state.get("debug_pipeline", {})

    if not debug_data:
        st.info("No hay información de debug aún")
        return

    for etapa, data in debug_data.items():

        st.markdown(f"### 🔍 {etapa}")

        if isinstance(data, dict):
            st.json(data)

        elif hasattr(data, "head"):
            st.dataframe(data.head(10), use_container_width=True)

        else:
            st.write(data)
