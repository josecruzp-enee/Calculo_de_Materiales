import streamlit as st


def debug_guardar(etapa: str, data):
    if "debug_pipeline" not in st.session_state:
        st.session_state["debug_pipeline"] = {}

    st.session_state["debug_pipeline"][etapa] = data
