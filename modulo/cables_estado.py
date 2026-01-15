# -*- coding: utf-8 -*-
"""
cables_estado.py
Inicialización y manejo de session_state relacionado a cables.
"""

from __future__ import annotations
import pandas as pd


def _ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Asegura columnas mínimas para el editor de cables.
    """
    if df is None or df.empty:
        df = pd.DataFrame()

    cols = list(df.columns) if not df.empty else []
    requeridas = ["Tipo", "Calibre", "Config", "Longitud", "Unidad", "Conductores", "Incluir"]

    out = df.copy()
    for c in requeridas:
        if c not in cols:
            # defaults razonables
            if c == "Longitud":
                out[c] = 0.0
            elif c == "Incluir":
                out[c] = True
            elif c == "Unidad":
                out[c] = "m"
            else:
                out[c] = ""
    return out


def _init_state(st) -> None:
    """
    Inicializa keys usadas por el módulo.
    """
    st.session_state.setdefault("cables_editor", None)
    st.session_state.setdefault("cables_proyecto", [])
    st.session_state.setdefault("cables_proyecto_df", pd.DataFrame())
    st.session_state.setdefault("cables_buffer_df", pd.DataFrame())
    st.session_state.setdefault("toast_cables_ok", False)
    st.session_state.setdefault("toast_cables_reset", False)

    # datos_proyecto existe en tu app
    st.session_state.setdefault("datos_proyecto", {})


def _editor_df_actual(st) -> pd.DataFrame:
    """
    Fuente del editor: cables_buffer_df si existe, si no cables_proyecto_df, si no lista.
    """
    import pandas as pd

    buf = st.session_state.get("cables_buffer_df")
    if isinstance(buf, pd.DataFrame) and not buf.empty:
        df = buf.copy()
    else:
        dfdf = st.session_state.get("cables_proyecto_df")
        if isinstance(dfdf, pd.DataFrame) and not dfdf.empty:
            df = dfdf.copy()
        else:
            lst = st.session_state.get("cables_proyecto", [])
            df = pd.DataFrame(lst) if isinstance(lst, list) else pd.DataFrame()

    df = _ensure_columns(df)
    return df
