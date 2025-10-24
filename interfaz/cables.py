# -*- coding: utf-8 -*-
# interfaz/cables.py

import streamlit as st
from modulo.configuracion_cables import seccion_cables

def seccion_cables_proyecto() -> None:
    """UI de cables (tabla única). Guarda resultado en session_state si aplica."""
    st.subheader("⚙️ Configuración de Cables del Proyecto")
    resultado = seccion_cables()  # tu función devuelve lista/df según tu versión

    if resultado:
        st.session_state["datos_proyecto"]["cables_proyecto"] = resultado
        st.session_state["cables_proyecto"] = resultado
        st.success("✅ Calibres registrados correctamente.")

    st.markdown("---")
