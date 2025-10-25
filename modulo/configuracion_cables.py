 # -*- coding: utf-8 -*-
"""
configuracion_cables.py
Editor estable (con Guardar/Descartar) → tabla formal de resultados.
- Buffer de edición en session_state (cables_buffer_df).
- Datos “oficiales” en cables_proyecto_df / cables_proyecto.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
from typing import List, Dict

# ----------- Catálogos -----------
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

# ----------- Estado base -----------
def _init_state():
    if "cables_proyecto_df" not in st.session_state:
        st.session_state["cables_proyecto_df"] = pd.DataFrame(
            columns=["Tipo","Configuración","Calibre","Longitud (m)","Total Cable (m)"]
        )
    if st.session_state["cables_proyecto_df"].empty:
        st.session_state["cables_proyecto_df"] = pd.DataFrame([{
            "Tipo":"MT","Configuración":"1F","Calibre":"1/0 ASCR",
            "Longitud (m)":0.0,"Total Cable (m)":0.0
        }])
    # Buffer de edición (copia ampliada con columna Eliminar)
    if "cables_buffer_df" not in st.session_state:
        buf = st.session_state["cables_proyecto_df"].copy()
        if "__DEL__" not in buf.columns:
            buf.insert(0, "__DEL__", False)
        st.session_state["cables_buffer_df"] = buf

# ----------- Validación + cálculo -----------
def _validar_y_calcular(df_in: pd.DataFrame) -> pd.DataFrame:
    cfgs = get_configs_por_tipo()
    cal_por_tipo = get_calibres()

    # elimina filas marcadas
    if "__DEL__" in df_in.columns:
        df_in = df_in[~df_in["__DEL__"]].drop(columns="__DEL__", errors="ignore")

    rows = []
    for _, row in df_in.fillna("").iterrows():
        if not row.get("Tipo"):  # ignora filas vacías
            continue
        tipo = str(row["Tipo"]).strip()

        cfg_permitidas = cfgs.get(tipo, ["Única"])
        cfg = str(row.get("Configuración") or cfg_permitidas[0])
        if cfg not in cfg_permitidas:
            cfg = cfg_permitidas[0]

        cal_list = cal_por_tipo.get(tipo, get_calibres_union())
        cal = str(row.get("Calibre") or (cal_list[0] if cal_list else ""))
        if cal not in cal_list and cal_list:
            cal = cal_list[0]

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

    cols = ["Tipo","Configuración","Calibre","Longitud (m)","Total Cable (m)"]
    return pd.DataFrame(rows, columns=cols)

def _persistir_oficial(df: pd.DataFrame) -> None:
    st.session_state["cables_proyecto_df"] = df.copy()
    lista = df.to_dict(orient="records")
    st.session_state["cables_proyecto"] = lista
    st.session_state.setdefault("datos_proyecto", {})
    st.session_state["datos_proyecto"]["cables_proyecto"] = lista

# ----------- Estilo tabla formal -----------
def _styler_formal(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    return (
        df.style.hide(axis="index")
        .format({"Longitud (m)":"{:,.2f}","Total Cable (m)":"{:,.2f}"}, na_rep="—")
        .set_table_styles(
            [
                {"selector":"table",
                 "props":[("border-collapse","separate"),("border-spacing","0"),
                          ("border","1px solid #E5E7EB"),("border-radius","12px"),
                          ("overflow","hidden"),("width","100%")]},
                {"selector":"thead th",
                 "props":[("background-color","#F3F4F6"),("color","#111827"),
                          ("font-weight","700"),("font-size","13.5px"),
                          ("text-align","left"),("padding","10px 12px"),
                          ("border-bottom","1px solid #E5E7EB")]},
                {"selector":"tbody td",
                 "props":[("padding","10px 12px"),("border-bottom","1px solid #F1F5F9"),
                          ("font-size","13px")]}
            ]
        )
        .apply(lambda s: ["background-color: #FBFBFE" if i % 2 else "" for i in range(len(s))], axis=0)
    )

# ----------- Sección principal -----------
def seccion_cables():
    _init_state()

    # ---------- 1) EDITOR (en formulario) ----------
    st.markdown("### 2️⃣ ✏️ Configuración y calibres de conductores (editor)")
    st.caption("Edita el buffer y pulsa **Guardar** para aplicar. Marca **Eliminar** para borrar filas.")

    with st.form("editor_cables", clear_on_submit=False):
        edited = st.data_editor(
            st.session_state["cables_buffer_df"],
            key="cables_editor",
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_order=["__DEL__", "Tipo", "Configuración", "Calibre", "Longitud (m)", "Total Cable (m)"],
            column_config={
                "__DEL__": st.column_config.CheckboxColumn("Eliminar", width="small",
                                                           help="Marca y luego pulsa Guardar para borrar"),
                "Tipo": st.column_config.SelectboxColumn("Tipo", options=get_tipos(), required=True, width="small"),
                "Configuración": st.column_config.SelectboxColumn("Configuración", options=get_configs_union(),
                                                                  required=True, width="small"),
                "Calibre": st.column_config.SelectboxColumn("Calibre", options=get_calibres_union(),
                                                            required=True, width="medium"),
                "Longitud (m)": st.column_config.NumberColumn("Longitud (m)", min_value=0.0, step=10.0, format="%.2f"),
                "Total Cable (m)": st.column_config.NumberColumn("Total Cable (m)", disabled=True, format="%.2f",
                                                                 help="Longitud × Nº de conductores"),
            },
        )
        c1, c2 = st.columns([1,1])
        guardar = c1.form_submit_button("💾 Guardar cambios", type="primary", use_container_width=True)
        descartar = c2.form_submit_button("↩️ Descartar cambios", use_container_width=True)

    # Manejo de botones
    if guardar:
        df_validado = _validar_y_calcular(edited)
        _persistir_oficial(df_validado)
        # refresca buffer desde oficial (y reañade columna Eliminar)
        buf = df_validado.copy()
        if "__DEL__" not in buf.columns:
            buf.insert(0, "__DEL__", False)
        st.session_state["cables_buffer_df"] = buf
        st.success("✅ Cambios guardados correctamente.")
    elif descartar:
        # vuelve a la versión oficial
        buf = st.session_state["cables_proyecto_df"].copy()
        if "__DEL__" not in buf.columns:
            buf.insert(0, "__DEL__", False)
        st.session_state["cables_buffer_df"] = buf
        st.info("Cambios descartados.")

    st.markdown("---")

    # ---------- 2) RESULTADOS (tabla formal) ----------
    st.markdown("### 2️⃣ ⚡ Configuración y calibres de conductores (tabla)")
    st.caption("Resultados guardados (presentación limpia sin celdas editables).")

    # CSS para bordes redondeados del contenedor
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
        df_out = df_out.reindex(columns=["Tipo","Configuración","Calibre","Longitud (m)","Total Cable (m)"])
        st.table(_styler_formal(df_out))
        st.markdown(f"**🧮 Total Global de Cable:** {df_out['Total Cable (m)'].sum():,.2f} m")

    # Devuelve lista de dicts (coherente con el resto de la app)
    return st.session_state.get("cables_proyecto", [])
