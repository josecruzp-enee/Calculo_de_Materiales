# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd


def seccion_debug():

    st.subheader("🧠 Debug del sistema")

    debug_data = st.session_state.get("debug_pipeline", {})

    if not debug_data:
        st.info("No hay información de debug aún")
        return

    for etapa, data in debug_data.items():

        st.markdown(f"### 🔍 {etapa}")

        # =====================================================
        # 🔥 SI ES DICCIONARIO → ITERAR
        # =====================================================
        if isinstance(data, dict):

            for k, v in data.items():

                st.markdown(f"#### {k}")

                # 🔥 CASO 1: DataFrame directo
                if isinstance(v, pd.DataFrame):
                    st.dataframe(v, use_container_width=True)

                # 🔥 CASO 2: dict → convertir a tabla
                elif isinstance(v, dict):
                    try:
                        df = pd.DataFrame(v)

                        # evitar tablas vacías feas
                        if not df.empty:
                            st.dataframe(df, use_container_width=True)
                        else:
                            st.write(v)

                    except:
                        st.write(v)

                # 🔥 CASO 3: lista → tabla
                elif isinstance(v, list):
                    try:
                        df = pd.DataFrame(v)
                        st.dataframe(df, use_container_width=True)
                    except:
                        st.write(v)

                # 🔥 OTROS
                else:
                    st.write(v)

        # =====================================================
        # 🔥 SI ES DATAFRAME DIRECTO
        # =====================================================
        elif isinstance(data, pd.DataFrame):
            st.dataframe(data, use_container_width=True)

        # =====================================================
        # 🔥 FALLBACK
        # =====================================================
        else:
            st.write(data)
