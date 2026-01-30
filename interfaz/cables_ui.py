# -*- coding: utf-8 -*-
"""
cables_ui.py
UI de Streamlit para gestionar cables del proyecto.
"""

from __future__ import annotations
import pandas as pd

from core.cables_catalogo import get_tipos, get_calibres_union, get_configs_union
from .cables_estado import _init_state, _editor_df_actual
from servicios.cables_logica import _persistir_oficial, _resumen_por_calibre, _validar_y_calcular



def seccion_cables():
    import streamlit as st

    _init_state(st)
    _persistir_oficial(st)

    st.subheader("Cables del proyecto")

    df_base = _editor_df_actual(st)

    # --- Normalizar columnas mínimas para el editor (por si viene vacío o con columnas viejas) ---
    # Queremos SOLO: Tipo, Calibre, Config, Longitud
    cols_min = ["Tipo", "Calibre", "Config", "Longitud"]
    if df_base is None or not isinstance(df_base, pd.DataFrame) or df_base.empty:
        df_base = pd.DataFrame(columns=cols_min)
    else:
        # si vienen columnas extra (Unidad/Incluir/etc), no las mostramos
        for c in cols_min:
            if c not in df_base.columns:
                df_base[c] = ""
        df_base = df_base[cols_min].copy()

    # Column config (si tu versión de Streamlit lo soporta)
    colcfg = None
    try:
        from streamlit.column_config import SelectboxColumn, NumberColumn
        colcfg = {
            "Tipo": SelectboxColumn("Tipo", options=get_tipos(), required=True, width="small"),
            "Calibre": SelectboxColumn("Calibre", options=get_calibres_union(), required=True, width="large"),
            "Config": SelectboxColumn("Config", options=get_configs_union(), required=True, width="small"),
            "Longitud": NumberColumn("Longitud (m)", min_value=0.0, step=1.0, format="%.2f", width="small"),
        }
    except Exception:
        colcfg = None

    with st.form("form_cables"):
        st.caption("Editá la lista de cables. El total se calcula automáticamente según la configuración (1F/2F/3F).")

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

        # --- Vista resumida (más útil que el json largo) ---
        if df_ok is not None and not df_ok.empty:
            st.success("Cables guardados.")

            # Mostrar tabla calculada (incluye Total Cable (m) y Conductores calculados)
            cols_show = [c for c in ["Tipo", "Calibre", "Config", "Longitud", "Conductores", "Total Cable (m)"] if c in df_ok.columns]
            st.dataframe(df_ok[cols_show], use_container_width=True, hide_index=True)

            resumen = _resumen_por_calibre(df_ok)
            if resumen:
                st.write("Resumen (longitud por calibre):")
                st.json(resumen)
        else:
            st.info("Guardado: no hay filas válidas (faltan datos).")

        st.rerun()
