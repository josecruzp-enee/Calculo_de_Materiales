# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd


# =========================================================
# DEBUG BACKEND (OBLIGATORIO)
# =========================================================
def debug_guardar(clave: str, valor):
    try:
        if "debug_pipeline" not in st.session_state:
            st.session_state["debug_pipeline"] = {}

        st.session_state["debug_pipeline"][clave] = valor
    except Exception:
        pass


# =========================================================
# DEBUG UI
# =========================================================
def seccion_debug():

    st.subheader("🧠 Debug del sistema")

    debug_data = st.session_state.get("debug_pipeline", {})

    if not isinstance(debug_data, dict) or not debug_data:
        st.info("No hay información de debug aún")
        return

    for etapa, data in debug_data.items():

        st.markdown(f"### 🔍 {etapa}")

        try:
            if isinstance(data, dict):
                limpio = {str(k): str(v)[:200] for k, v in data.items()}
                st.json(limpio)

            elif isinstance(data, pd.DataFrame):
                if data.empty:
                    st.warning("DataFrame vacío")
                else:
                    st.caption(f"Filas: {len(data)}")
                    st.dataframe(data.head(10), use_container_width=True)

            elif isinstance(data, (list, tuple, set)):
                limpio = [str(x) for x in list(data)[:20]]
                st.write(limpio)

            elif hasattr(data, "__dict__"):
                limpio = {str(k): str(v)[:200] for k, v in vars(data).items()}
                st.json(limpio)

            else:
                st.write(str(data))

        except Exception as e:
            st.error(f"Error mostrando debug: {e}")
