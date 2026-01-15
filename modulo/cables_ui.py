# -*- coding: utf-8 -*-
"""
cables_ui.py
UI de Streamlit para gestionar cables del proyecto.
"""

from __future__ import annotations
import pandas as pd

from .cables_catalogo import get_tipos, get_calibres_union, get_configs_union
from .cables_estado import _init_state, _editor_df_actual
from .cables_logica import _persistir_oficial, _resumen_por_calibre, _validar_y_calcular


def seccion_cables():
    import streamlit as st

    _init_state(st)
    _persistir_oficial(st)

    st.subheader("Cables del proyecto")

    df_base = _editor_df_actual(st)

    # Column config (si tu versión de Streamlit lo soporta)
    colcfg = None
    try:
        from streamlit.column_config import SelectboxColumn, NumberColumn, CheckboxColumn
        colcfg = {
            "Tipo": SelectboxColumn("Tipo", options=get_tipos(), required=True),
            "Calibre": SelectboxColumn("Calibre", options=get_calibres_union(), required=True),
            "Config": SelectboxColumn("Config", options=get_configs_union(), required=False),
            "Longitud": NumberColumn("Longitud", min_value=0.0, step=1.0),
            "Unidad": SelectboxColumn("Unidad", options=["m", "km", "pies", "pie", "ft"], required=False),
            "Incluir": CheckboxColumn("Incluir"),
        }
    except Exception:
        colcfg = None

    with st.form("form_cables"):
        st.caption("Editá la lista de cables. Si algo no aplica, desmarcá 'Incluir'.")
        df_edit = st.data_editor(
            df_base,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config=colcfg,
        )

        ok = st.form_submit_button("✅ Guardar cables")
        reset = st.form_submit_button("🧹 Resetear")

    if reset:
        st.session_state["cables_buffer_df"] = pd.DataFrame()
        st.session_state["cables_proyecto_df"] = pd.DataFrame()
        st.session_state["cables_proyecto"] = []
        st.success("Cables reseteados.")
        st.rerun()

    if ok:
        df_ok = _validar_y_calcular(df_edit)
        st.session_state["cables_proyecto_df"] = df_ok.copy()
        st.session_state["cables_proyecto"] = df_ok.to_dict(orient="records")

        # guardar también dentro de datos_proyecto
        dp = st.session_state.get("datos_proyecto", {}) or {}
        dp["cables_proyecto"] = st.session_state["cables_proyecto"]
        st.session_state["datos_proyecto"] = dp

        resumen = _resumen_por_calibre(df_ok)
        if resumen:
            st.success("Cables guardados.")
            st.write("Resumen (longitud por calibre):")
            st.json(resumen)
        else:
            st.info("Cables guardados (sin longitudes).")
        st.rerun()
