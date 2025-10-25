# -*- coding: utf-8 -*-
"""
modulo/configuracion_cables.py

Sección Cables con experiencia PRO:
- Editor estable (formulario con Guardar/Descartar) y borrar filas con checkbox.
- Validación por tipo y cálculo automático del total.
- Resultados con tabla formal (no 'excel'), KPIs y total global.
- Un solo título: '2️⃣ ⚡ Configuración y calibres de conductores (tabla)'.

Datos oficiales:
  st.session_state['cables_proyecto_df']  -> DataFrame
  st.session_state['cables_proyecto']     -> lista de dicts
  st.session_state['datos_proyecto']['cables_proyecto'] -> para otros módulos
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
from typing import List, Dict

# =========================
# Catálogos
# =========================
def get_tipos() -> List[str]:
    return ["MT", "BT", "N", "HP", "Retenida"]

def get_calibres() -> Dict[str, List[str]]:
    return {
        "MT": ["2 ASCR", "1/0 ASCR", "2/0 ASCR", "3/0 ASCR", "4/0 ASCR", "266.8 MCM", "336 MCM"],
        "BT": ["2 WP", "1/0 WP", "2/0 WP", "3/0 WP", "4/0 WP"],
        "N":  ["2 ASCR", "1/0 ASCR", "2/0 ASCR", "3/0 ASCR", "4/0 ASCR"],
        "HP": ["2 WP", "1/0 WP", "2/0 WP"],
        "Retenida": ["1/4", "5/8", "3/4"],
    }

def get_configs_por_tipo() -> Dict[str, List[str]]:
    return {
        "MT": ["1F", "2F", "3F"],
        "BT": ["2F", "2F+N", "2F+HP+N"],
        "N":  ["N"],
        "HP": ["1F+N", "2F"],
        "Retenida": ["Única"],
    }

def get_configs_union() -> List[str]:
    # Para el editor (validación fina por tipo)
    return ["Única", "N", "1F", "1F+N", "2F", "2F+N", "2F+HP+N", "3F"]

def get_calibres_union() -> List[str]:
    cal = get_calibres()
    return list(dict.fromkeys(c for lista in cal.values() for c in lista))

def conductores_de(cfg: str) -> int:
    c = (cfg or "").strip().upper()
    if c in ("ÚNICA", "N", "1F"): return 1
    if c in ("1F+N", "2F"):       return 2
    if c in ("3F", "2F+N"):       return 3
    if c == "2F+HP+N":            return 4
    return 1


# =========================
# Estado y helpers
# =========================
COLS_OFICIALES = ["Tipo", "Configuración", "Calibre", "Longitud (m)", "Total Cable (m)"]

def _init_state() -> None:
    """Crea data oficial y buffer de edición."""
    if "cables_proyecto_df" not in st.session_state:
        st.session_state["cables_proyecto_df"] = pd.DataFrame(columns=COLS_OFICIALES)

    # Fila guía si está vacío
    if st.session_state["cables_proyecto_df"].empty:
        st.session_state["cables_proyecto_df"] = pd.DataFrame([{
            "Tipo": "MT", "Configuración": "1F", "Calibre": "1/0 ASCR",
            "Longitud (m)": 0.0, "Total Cable (m)": 0.0
        }])

    # Buffer de edición (con columna Eliminar)
    if "cables_buffer_df" not in st.session_state:
        buf = st.session_state["cables_proyecto_df"].copy()
        if "__DEL__" not in buf.columns:
            buf.insert(0, "__DEL__", False)
        st.session_state["cables_buffer_df"] = buf

def _validar_y_calcular(df_in: pd.DataFrame) -> pd.DataFrame:
    """Normaliza por tipo y calcula total; respeta borrados del checkbox."""
    cfgs = get_configs_por_tipo()
    cal_por_tipo = get_calibres()

    # Borrar filas marcadas (dtype seguro)
    if "__DEL__" in df_in.columns:
        mask = df_in["__DEL__"].fillna(False)
        if mask.dtype != bool:
            mask = mask.astype(bool, copy=False)
        df_in = df_in[~mask].drop(columns="__DEL__", errors="ignore")

    rows = []
    for _, row in df_in.fillna("").iterrows():
        if not row.get("Tipo"):
            continue

        tipo = str(row["Tipo"]).strip()

        # Configuración permitida por tipo
        cfg_ok = cfgs.get(tipo, ["Única"])
        cfg = str(row.get("Configuración") or cfg_ok[0])
        if cfg not in cfg_ok:
            cfg = cfg_ok[0]

        # Calibre permitido por tipo
        cal_ok = cal_por_tipo.get(tipo, get_calibres_union())
        cal = str(row.get("Calibre") or (cal_ok[0] if cal_ok else ""))
        if cal not in cal_ok and cal_ok:
            cal = cal_ok[0]

        # Longitud y total
        try:
            L = float(row.get("Longitud (m)", 0.0))
        except Exception:
            L = 0.0

        rows.append({
            "Tipo": tipo,
            "Configuración": cfg,
            "Calibre": cal,
            "Longitud (m)": L,
            "Total Cable (m)": L * conductores_de(cfg),
        })

    return pd.DataFrame(rows, columns=COLS_OFICIALES)

def _persistir_oficial(df: pd.DataFrame) -> None:
    """Guarda versión oficial y sincroniza estructuras auxiliares."""
    st.session_state["cables_proyecto_df"] = df.copy()
    lista = df.to_dict(orient="records")
    st.session_state["cables_proyecto"] = lista
    st.session_state.setdefault("datos_proyecto", {})
    st.session_state["datos_proyecto"]["cables_proyecto"] = lista

def _kpis(df: pd.DataFrame) -> None:
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Filas", len(df))
    with c2: st.metric("Longitud (m)", f"{df['Longitud (m)'].sum():,.2f}")
    with c3: st.metric("Total Cable (m)", f"{df['Total Cable (m)'].sum():,.2f}")

def _styler_formal(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Tabla formal: encabezado gris, zebra, bordes finos, esquinas redondeadas."""
    return (
        df.style.hide(axis="index")
        .format({"Longitud (m)": "{:,.2f}", "Total Cable (m)": "{:,.2f}"}, na_rep="—")
        .set_table_styles(
            [
                {"selector": "table",
                 "props": [("border-collapse", "separate"),
                           ("border-spacing", "0"),
                           ("border", "1px solid #E5E7EB"),
                           ("border-radius", "12px"),
                           ("overflow", "hidden"),
                           ("width", "100%")]},
                {"selector": "thead th",
                 "props": [("background-color", "#F3F4F6"),
                           ("color", "#111827"),
                           ("font-weight", "700"),
                           ("font-size", "13.5px"),
                           ("text-align", "left"),
                           ("padding", "10px 12px"),
                           ("border-bottom", "1px solid #E5E7EB")]},
                {"selector": "tbody td",
                 "props": [("padding", "10px 12px"),
                           ("border-bottom", "1px solid #F1F5F9"),
                           ("font-size", "13px")]},
            ]
        )
        .apply(lambda s: ["background-color: #FBFBFE" if i % 2 else "" for i in range(len(s))], axis=0)
    )


# =========================
# Sección principal
# =========================
def seccion_cables():
    _init_state()

    # ---------- TÍTULO ÚNICO ----------
    st.markdown("## 2️⃣ ⚡ Configuración y calibres de conductores (tabla)")

    # ---------- EDITOR (formulario estable) ----------
    st.caption("Edita el buffer y pulsa **Guardar**. Marca **Eliminar** para borrar filas.")
    with st.form("editor_cables", clear_on_submit=False):
        edited = st.data_editor(
            st.session_state["cables_buffer_df"],
            key="cables_editor",
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_order=["__DEL__", "Tipo", "Configuración", "Calibre", "Longitud (m)", "Total Cable (m)"],
            column_config={
                "__DEL__": st.column_config.CheckboxColumn(
                    "Eliminar", width="small",
                    help="Marca y pulsa Guardar para borrar"
                ),
                "Tipo": st.column_config.SelectboxColumn(
                    "Tipo", options=get_tipos(), required=True, width="small"
                ),
                "Configuración": st.column_config.SelectboxColumn(
                    "Configuración", options=get_configs_union(), required=True, width="small"
                ),
                "Calibre": st.column_config.SelectboxColumn(
                    "Calibre", options=get_calibres_union(), required=True, width="medium"
                ),
                "Longitud (m)": st.column_config.NumberColumn(
                    "Longitud (m)", min_value=0.0, step=10.0, format="%.2f"
                ),
                "Total Cable (m)": st.column_config.NumberColumn(
                    "Total Cable (m)", disabled=True, format="%.2f",
                    help="Longitud × Nº de conductores"
                ),
            },
        )
        c1, c2 = st.columns([1, 1])
        guardar = c1.form_submit_button("💾 Guardar cambios", type="primary", use_container_width=True)
        descartar = c2.form_submit_button("↩️ Descartar cambios", use_container_width=True)

    # Botones
    if guardar:
        df_validado = _validar_y_calcular(edited)
        _persistir_oficial(df_validado)
        buf = df_validado.copy()
        if "__DEL__" not in buf.columns:
            buf.insert(0, "__DEL__", False)
        st.session_state["cables_buffer_df"] = buf
        st.success("✅ Cambios guardados.")
    elif descartar:
        buf = st.session_state["cables_proyecto_df"].copy()
        if "__DEL__" not in buf.columns:
            buf.insert(0, "__DEL__", False)
        st.session_state["cables_buffer_df"] = buf
        st.info("Cambios descartados.")

    st.markdown("---")

    # ---------- RESULTADOS (solo tabla formal con columna 'Ítem') ----------
    # CSS de contenedor con esquinas redondeadas
    st.markdown("""
    <style>
      .stTable > div { border-radius: 12px; overflow: hidden; border: 1px solid #E5E7EB; }
      .stTable thead tr th:first-child { border-top-left-radius: 12px; }
      .stTable thead tr th:last-child  { border-top-right-radius: 12px; }
      .stTable tbody tr:last-child td:first-child { border-bottom-left-radius: 12px; }
      .stTable tbody tr:last-child td:last-child  { border-bottom-right-radius: 12px; }
    </style>
    """, unsafe_allow_html=True)

    df_out = st.session_state["cables_proyecto_df"].copy()
    if df_out.empty:
      st.info("No hay datos guardados.")
    else:
      # Orden oficial y agregar Ítem (1..n)
      df_out = df_out.reindex(columns=COLS_OFICIALES)
      df_disp = df_out.copy()
      df_disp.insert(0, "Ítem", range(1, len(df_disp) + 1))

      # “Oculta” visualmente el índice (evita 0,1,... a la izquierda)
      df_disp.index = [""] * len(df_disp)
      df_disp.index.name = ""  # sin título de índice

      # Estilo formal + centrado de la columna Ítem
      sty = _styler_formal(df_disp).set_properties(
        subset=pd.IndexSlice[:, ["Ítem"]],
        **{"text-align": "center", "font-weight": "600"}
      )

      st.table(sty)


    # Devuelve lista (API histórica de tu app)
    return st.session_state.get("cables_proyecto", [])

