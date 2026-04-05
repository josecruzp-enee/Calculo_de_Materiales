# -*- coding: utf-8 -*-
"""
cables_ui.py
UI de Streamlit para gestionar cables del proyecto.
"""

from __future__ import annotations
import pandas as pd
import streamlit as st

from core.cables_catalogo import (
    get_tipos,
    get_calibres_union,
    get_configs_union,
)

from .cables_estado import _init_state, _editor_df_actual
from servicios.cables_logica import (
    _resumen_por_calibre,
    _validar_y_calcular,
)


# =========================================================
# UI PRINCIPAL
# =========================================================

def seccion_cables() -> dict:

    # Inicializar estado
    _init_state(st)

    st.subheader("Cables del proyecto")

    df_base = _editor_df_actual(st)

    # =====================================================
    # NORMALIZAR DF
    # =====================================================

    cols_min = ["Tipo", "Calibre", "Config", "Longitud"]

    if df_base is None or not isinstance(df_base, pd.DataFrame) or df_base.empty:
        df_base = pd.DataFrame(columns=cols_min)
    else:
        for c in cols_min:
            if c not in df_base.columns:
                df_base[c] = ""
        df_base = df_base[cols_min].copy()

    # =====================================================
    # CONFIGURACIÓN DE COLUMNAS
    # =====================================================

    colcfg = None
    try:
        from streamlit.column_config import SelectboxColumn, NumberColumn

        colcfg = {
            "Tipo": SelectboxColumn("Tipo", options=get_tipos(), required=True),
            "Calibre": SelectboxColumn("Calibre", options=get_calibres_union(), required=True),
            "Config": SelectboxColumn("Config", options=get_configs_union(), required=True),
            "Longitud": NumberColumn("Longitud (m)", min_value=0.0, step=1.0, format="%.2f"),
        }
    except Exception:
        pass

    # =====================================================
    # FORMULARIO
    # =====================================================

    with st.form("form_cables"):

        st.caption("Editá la lista de cables.")

        df_edit = st.data_editor(
            df_base,
            width="stretch",
            hide_index=True,
            num_rows="dynamic",
            column_config=colcfg,
        )

        col1, col2 = st.columns(2)

        with col1:
            ok = st.form_submit_button("✅ Guardar cables")

        with col2:
            reset = st.form_submit_button("🧹 Resetear")

    # =====================================================
    # RESET
    # =====================================================

    if reset:
        st.session_state["cables_buffer_df"] = pd.DataFrame()
        st.session_state["cables_proyecto_df"] = pd.DataFrame()
        st.session_state["cables_proyecto"] = []

        dp = st.session_state.get("datos_proyecto", {}) or {}
        dp["cables_proyecto"] = []
        st.session_state["datos_proyecto"] = dp

        st.success("Cables reseteados.")
        st.rerun()

    # =====================================================
    # GUARDAR
    # =====================================================

    if ok:

        df_ok = _validar_y_calcular(df_edit)

        if df_ok is None or df_ok.empty:
            st.warning("⚠️ No hay datos válidos.")
            return {
                "ok": False,
                "cables": [],
                "df": pd.DataFrame(),
            }

        registros = df_ok.to_dict(orient="records")

        st.session_state["cables_proyecto_df"] = df_ok.copy()
        st.session_state["cables_proyecto"] = registros

        dp = st.session_state.get("datos_proyecto", {}) or {}
        dp["cables_proyecto"] = registros
        st.session_state["datos_proyecto"] = dp

        st.success("Cables guardados correctamente.")

        cols_show = [
            c for c in [
                "Tipo",
                "Calibre",
                "Config",
                "Longitud",
                "Conductores",
                "Total Cable (m)",
            ]
            if c in df_ok.columns
        ]

        st.dataframe(df_ok[cols_show], width="stretch", hide_index=True)

        resumen = _resumen_por_calibre(df_ok)

        if resumen:
            st.write("Resumen (longitud por calibre):")
            st.json(resumen)

        st.rerun()

    # =====================================================
    # SALIDA ESTÁNDAR
    # =====================================================

    return {
        "ok": True,
        "cables": st.session_state.get("cables_proyecto", []),
        "df": st.session_state.get("cables_proyecto_df", pd.DataFrame()),
    }
