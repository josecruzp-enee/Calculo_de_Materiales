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
# CONSTANTES DE CABLES
# =========================================================

CALIBRE_MT_DEFAULT = "Cable de Aluminio ACSR # 1/0 AWG Raven"
CALIBRE_BT_DEFAULT = "Cable de Aluminio Forrado WP # 3/0 AWG Fig"
CALIBRE_N_DEFAULT = "Cable de Aluminio ACSR # 2 AWG Sparrow"
CALIBRE_HP_DEFAULT = "Cable de Aluminio Forrado WP # 2 AWG Peach"


# =========================================================
# HELPERS GENERALES
# =========================================================

def _texto(valor) -> str:
    return str(valor or "").strip()


def _texto_upper(valor) -> str:
    return _texto(valor).upper()


def _numero(valor, default: float = 0.0) -> float:
    try:
        return float(pd.to_numeric(valor, errors="coerce"))
    except Exception:
        return default


def _normalizar_config(config: str) -> str:
    return _texto_upper(config).replace(" ", "")


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
            "Longitud": 240.0,
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

    if "Descripcion" in out.columns and "Servicio" not in out.columns:
        out["Servicio"] = out["Descripcion"]

    if "Tipo" in out.columns and "Usa Cable" not in out.columns:
        out["Usa Cable"] = out["Tipo"]

    for c in cols:
        if c not in out.columns:
            out[c] = 0.0 if c == "Longitud" else ""

    out = out[cols].copy()

    out["Circuito"] = out["Circuito"].astype(str).str.strip()
    out["Servicio"] = out["Servicio"].astype(str).str.strip()
    out["Usa Cable"] = out["Usa Cable"].astype(str).str.strip().str.upper()
    out["Tension"] = out["Tension"].astype(str).str.strip()
    out["Config Circuito"] = out["Config Circuito"].astype(str).str.strip().str.upper()
    out["Longitud"] = pd.to_numeric(
        out["Longitud"],
        errors="coerce",
    ).fillna(0.0)

    # NO eliminar longitudes en cero.
    # El cero es válido cuando el usuario quiere dejar el circuito sin longitud.
    return out.reset_index(drop=True)

# =========================================================
# GENERAR CABLES DESDE CIRCUITOS
# =========================================================

def _crear_fila_cable(
    *,
    tipo: str,
    calibre: str,
    config: str,
    longitud: float,
    incluir: bool = True,
) -> dict:
    return {
        "Incluir": incluir,
        "Tipo": tipo,
        "Calibre": calibre,
        "Config": config,
        "Longitud": round(float(longitud), 2),
    }

def _cables_desde_circuito(row: pd.Series) -> list[dict]:
    tipo_base = _texto_upper(row.get("Usa Cable", ""))
    config = _normalizar_config(row.get("Config Circuito", ""))
    longitud = _numero(row.get("Longitud", 0), 0.0)

    if longitud <= 0:
        return []

    filas = []

    # =====================================================
    # LÍNEA PRIMARIA
    # =====================================================
    if tipo_base == "MT":
        filas.append(
            _crear_fila_cable(
                tipo="MT",
                calibre=CALIBRE_MT_DEFAULT,
                config=config,
                longitud=longitud,
            )
        )

        if "N" in config:
            filas.append(
                _crear_fila_cable(
                    tipo="N",
                    calibre=CALIBRE_N_DEFAULT,
                    config="N",
                    longitud=longitud,
                )
            )

        return filas

    # =====================================================
    # LÍNEA SECUNDARIA
    # =====================================================
    if tipo_base == "BT":
        filas.append(
            _crear_fila_cable(
                tipo="BT",
                calibre=CALIBRE_BT_DEFAULT,
                config=config,
                longitud=longitud,
            )
        )

        if "HP" in config:
            filas.append(
                _crear_fila_cable(
                    tipo="HP",
                    calibre=CALIBRE_HP_DEFAULT,
                    config="HP",
                    longitud=longitud,
                )
            )

        if "N" in config:
            filas.append(
                _crear_fila_cable(
                    tipo="N",
                    calibre=CALIBRE_N_DEFAULT,
                    config="N",
                    longitud=longitud,
                )
            )

        return filas

    # =====================================================
    # HILO PILOTO
    # =====================================================
    if tipo_base == "HP":
        filas.append(
            _crear_fila_cable(
                tipo="HP",
                calibre=CALIBRE_HP_DEFAULT,
                config="HP",
                longitud=longitud,
            )
        )

        if "N" in config:
            filas.append(
                _crear_fila_cable(
                    tipo="N",
                    calibre=CALIBRE_N_DEFAULT,
                    config="N",
                    longitud=longitud,
                )
            )

        return filas

    # =====================================================
    # NEUTRO INDEPENDIENTE
    # =====================================================
    if tipo_base == "N":
        filas.append(
            _crear_fila_cable(
                tipo="N",
                calibre=CALIBRE_N_DEFAULT,
                config="N",
                longitud=longitud,
            )
        )

        return filas

    return []


def _df_cables_desde_circuitos(
    df_circuitos: pd.DataFrame | None,
) -> pd.DataFrame:
    df_circuitos_ok = _normalizar_circuitos(df_circuitos)

    filas = []

    for _, row in df_circuitos_ok.iterrows():
        filas.extend(
            _cables_desde_circuito(row)
        )

    if not filas:
        return pd.DataFrame(
            columns=[
                "Tipo",
                "Calibre",
                "Config",
                "Longitud",
            ]
        )

    return pd.DataFrame(filas)


def _normalizar_cables(
    df: pd.DataFrame | None,
    df_circuitos: pd.DataFrame | None = None,
) -> pd.DataFrame:
    cols_min = [
        "Tipo",
        "Calibre",
        "Config",
        "Longitud",
    ]

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return _df_cables_desde_circuitos(df_circuitos)

    out = df.copy()

    for c in cols_min:
        if c not in out.columns:
            out[c] = 0.0 if c == "Longitud" else ""

    out = out[cols_min].copy()

    out["Tipo"] = out["Tipo"].astype(str).str.strip().str.upper()
    out["Calibre"] = out["Calibre"].astype(str).str.strip()
    out["Config"] = out["Config"].astype(str).str.strip().str.upper()
    out["Longitud"] = pd.to_numeric(
        out["Longitud"],
        errors="coerce",
    ).fillna(0.0)

    # NO eliminar longitudes en cero.
    # El cero es válido cuando el usuario quiere dejar el circuito sin longitud.
    return out.reset_index(drop=True)


# =========================================================
# UI PRINCIPAL
# =========================================================

def seccion_cables() -> dict:

    _init_state(st)

    st.subheader("Cables del proyecto")

    # =====================================================
    # NORMALIZAR DF CIRCUITOS
    # =====================================================

    df_circuitos_base = _normalizar_circuitos(
        st.session_state.get("circuitos_proyecto_df")
    )

    # =====================================================
    # NORMALIZAR DF CABLES
    # =====================================================

    df_base_raw = _editor_df_actual(st)

    df_base = _normalizar_cables(
        df_base_raw,
        df_circuitos_base,
    )

    # =====================================================
    # CONFIGURACIÓN DE COLUMNAS
    # =====================================================

    colcfg_cables = None
    colcfg_circuitos = None

    try:
        from streamlit.column_config import (
            SelectboxColumn,
            NumberColumn,
            TextColumn,
        )

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
                options=[
                    "MT",
                    "BT",
                    "N",
                    "HP",
                    "ACOMETIDA",
                    "OTRO",
                ],
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

        st.caption(
            "Editá la lista de cables. "
            "Si marcas la opción automática, esta tabla se genera desde los circuitos."
        )

        regenerar_desde_circuitos = st.checkbox(
            "Actualizar cables automáticamente desde circuitos al guardar",
            value=True,
            help=(
                "Si cambias longitudes o configuraciones en Circuitos del proyecto, "
                "la primera tabla se recalcula al guardar."
            ),
        )

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
        df_circuitos_default = _df_circuitos_default()
        df_cables_default = _df_cables_desde_circuitos(
            df_circuitos_default
        )

        st.session_state["cables_buffer_df"] = df_cables_default.copy()
        st.session_state["cables_proyecto_df"] = pd.DataFrame()
        st.session_state["cables_proyecto"] = []

        st.session_state["circuitos_proyecto_df"] = df_circuitos_default.copy()
        st.session_state["circuitos_proyecto"] = df_circuitos_default.to_dict(
            orient="records"
        )

        dp = st.session_state.get("datos_proyecto", {}) or {}
        dp["cables_proyecto"] = []
        dp["circuitos_proyecto"] = st.session_state["circuitos_proyecto"]
        st.session_state["datos_proyecto"] = dp

        st.success("Cables reseteados.")
        st.rerun()

    # =====================================================
    # GUARDAR
    # =====================================================

    if ok:

        df_circuitos_ok = _normalizar_circuitos(
            df_circuitos_edit
        )

        if regenerar_desde_circuitos:
            df_cables_para_calcular = _df_cables_desde_circuitos(
                df_circuitos_ok
            )
        else:
            df_cables_para_calcular = _normalizar_cables(
                df_edit,
                df_circuitos_ok,
            )

        df_ok = _validar_y_calcular(
            df_cables_para_calcular
        )

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

        st.session_state["cables_buffer_df"] = df_cables_para_calcular.copy()
        st.session_state["cables_proyecto_df"] = df_ok.copy()
        st.session_state["cables_proyecto"] = registros

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

        st.dataframe(
            df_ok[cols_show],
            width="stretch",
            hide_index=True,
        )

        st.write("Circuitos guardados:")

        st.dataframe(
            df_circuitos_ok,
            width="stretch",
            hide_index=True,
        )

        resumen = _resumen_por_calibre(
            df_ok
        )

        if resumen:
            st.write("Resumen (longitud por calibre):")
            st.json(resumen)

        st.rerun()

    # =====================================================
    # SALIDA ESTÁNDAR
    # =====================================================

    df_salida = st.session_state.get(
        "cables_proyecto_df",
        pd.DataFrame(),
    )

    df_circuitos_salida = st.session_state.get(
        "circuitos_proyecto_df",
        pd.DataFrame(),
    )

    return {
        "ok": True,
        "cables": df_salida.to_dict(orient="records"),
        "df": df_salida,
        "circuitos": df_circuitos_salida.to_dict(orient="records"),
    }
