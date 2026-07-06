# -*- coding: utf-8 -*-
"""
cables_ui.py
UI de Streamlit para gestionar cables del proyecto.
Incluye tabla adicional de configuración de circuitos sin romper salida anterior.
"""

from __future__ import annotations
import pandas as pd
import streamlit as st

from materiales.cables.cables_catalogo import (
    get_tipos,
    get_calibres_union,
    get_configs_union,
)

from interfaz.cables_estado import _init_state, _editor_df_actual
from materiales.cables.cables_logica import (
    _resumen_por_calibre,
    _validar_y_calcular,
)


# =========================================================
# HELPERS CIRCUITOS
# =========================================================

def _df_circuitos_default() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "Circuito": "LP-01",
            "Servicio": "Línea primaria",
            "Usa Cable": "MT",
            "Tension": "19.9/34.5 kV",
            "Config Circuito": "1F+N",
            "Longitud": 240.0,
        },
        {
            "Circuito": "LS-01",
            "Servicio": "Línea secundaria",
            "Usa Cable": "BT",
            "Tension": "120/240 V",
            "Config Circuito": "2F+N",
            "Longitud": 160.0,
        },
        {
            "Circuito": "HP-01",
            "Servicio": "Hilo piloto",
            "Usa Cable": "HP",
            "Tension": "120 V",
            "Config Circuito": "HP+N",
            "Longitud": 80.0,
        },
    ])

def _normalizar_circuitos(df: pd.DataFrame | None) -> pd.DataFrame:
    cols = [
        "Circuito",
        "Servicio",
        "Usa Cable",
        "Tension",
        "Config Circuito",
        "Longitud",
    ]

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return _df_circuitos_default()

    out = df.copy()

    # Compatibilidad con versión anterior
    if "Descripcion" in out.columns and "Servicio" not in out.columns:
        out["Servicio"] = out["Descripcion"]

    if "Tipo" in out.columns and "Usa Cable" not in out.columns:
        out["Usa Cable"] = out["Tipo"]

    for c in cols:
        if c not in out.columns:
            out[c] = 0.0 if c == "Longitud" else ""

    return out[cols].copy()
# =========================================================
# UI PRINCIPAL
# =========================================================

def seccion_cables() -> dict:

    _init_state(st)

    st.subheader("Cables del proyecto")

    df_base = _editor_df_actual(st)

    # =====================================================
    # NORMALIZAR DF CABLES EXISTENTE
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
    # NORMALIZAR DF CIRCUITOS NUEVO
    # =====================================================

    df_circuitos_base = _normalizar_circuitos(
        st.session_state.get("circuitos_proyecto_df")
    )

    # =====================================================
    # CONFIGURACIÓN DE COLUMNAS
    # =====================================================

    colcfg_cables = None
    colcfg_circuitos = None

    try:
        from streamlit.column_config import SelectboxColumn, NumberColumn, TextColumn

        configs_circuitos = [
            "1F+N",
            "2F+N",
            "3F+N",
            "2F+HP+N",
            "HP+N",
            "N",
            "PERSONALIZADO",
        ]

        colcfg_cables = {
            "Tipo": SelectboxColumn(
                "Tipo",
                options=get_tipos(),
                required=True,
            ),
            "Calibre": SelectboxColumn(
                "Calibre",
                options=get_calibres_union(),
                required=True,
            ),
            "Config": SelectboxColumn(
                "Config",
                options=get_configs_union(),
                required=True,
            ),
            "Longitud": NumberColumn(
                "Longitud (m)",
                min_value=0.0,
                step=1.0,
                format="%.2f",
            ),
        }

        colcfg_circuitos = {
            "Circuito": TextColumn(
                "Circuito",
                help="Ejemplo: LP-01, LP-02, LS-01, HP-01",
            ),
            "Servicio": TextColumn(
                "Servicio",
                help="Ejemplo: Línea primaria, Línea secundaria, Hilo piloto",
            ),
            "Usa Cable": SelectboxColumn(
                "Usa Cable",
                options=["MT", "BT", "N", "HP", "ACOMETIDA", "OTRO"],
                required=True,
            ),
            "Tension": TextColumn(
                "Tensión",
                help="Ejemplo: 19.9/34.5 kV, 120/240 V, 120 V",
            ),
            "Config Circuito": SelectboxColumn(
                "Config Circuito",
                options=configs_circuitos,
                required=True,
            ),
            "Longitud": NumberColumn(
                "Longitud (m)",
                min_value=0.0,
                step=1.0,
                format="%.2f",
            ),
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
            column_config=colcfg_cables,
            key="editor_cables_proyecto",
        )

        st.markdown("### Circuitos del proyecto")
        st.caption(
            "Cada fila representa un tramo independiente de línea. "
            "Puedes repetir líneas primarias, secundarias o HP sin que una excluya a la otra."
        )

        df_circuitos_edit = st.data_editor(
            df_circuitos_base,
            width="stretch",
            hide_index=True,
            num_rows="dynamic",
            column_config=colcfg_circuitos,
            key="editor_circuitos_proyecto",
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

        st.session_state["circuitos_proyecto_df"] = pd.DataFrame()
        st.session_state["circuitos_proyecto"] = []

        dp = st.session_state.get("datos_proyecto", {}) or {}
        dp["cables_proyecto"] = []
        dp["circuitos_proyecto"] = []
        st.session_state["datos_proyecto"] = dp

        st.success("Cables reseteados.")
        st.rerun()

    # =====================================================
    # GUARDAR
    # =====================================================

    if ok:

        df_ok = _validar_y_calcular(df_edit)
        df_circuitos_ok = _normalizar_circuitos(df_circuitos_edit)

        if df_ok is None or df_ok.empty:
            st.warning("⚠️ No hay datos válidos.")
            return {
                "ok": False,
                "cables": [],
                "df": pd.DataFrame(),
                "circuitos": df_circuitos_ok.to_dict(orient="records"),
            }

        registros = df_ok.to_dict(orient="records")
        registros_circuitos = df_circuitos_ok.to_dict(orient="records")

        st.session_state["cables_proyecto_df"] = df_ok.copy()
        st.session_state["circuitos_proyecto_df"] = df_circuitos_ok.copy()
        st.session_state["circuitos_proyecto"] = registros_circuitos

        dp = st.session_state.get("datos_proyecto", {}) or {}
        dp["cables_proyecto"] = registros
        dp["circuitos_proyecto"] = registros_circuitos
        st.session_state["datos_proyecto"] = dp

        st.success("Cables y circuitos guardados correctamente.")

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

        st.write("Circuitos guardados:")
        st.dataframe(df_circuitos_ok, width="stretch", hide_index=True)

        resumen = _resumen_por_calibre(df_ok)

        if resumen:
            st.write("Resumen (longitud por calibre):")
            st.json(resumen)

        st.rerun()

    # =====================================================
    # SALIDA ESTÁNDAR
    # =====================================================

    df_salida = st.session_state.get("cables_proyecto_df", pd.DataFrame())
    df_circuitos_salida = st.session_state.get("circuitos_proyecto_df", pd.DataFrame())

    return {
        "ok": True,
        "cables": df_salida.to_dict(orient="records"),
        "df": df_salida,
        "circuitos": df_circuitos_salida.to_dict(orient="records"),
    }
