
# -*- coding: utf-8 -*-
from __future__ import annotations
import streamlit as st
import pandas as pd
from typing import List, Dict

# ----------------- Catálogos (como los tienes) -----------------
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

# ----------------- Estado y helpers -----------------
COLS_OFICIALES = ["Tipo", "Configuración", "Calibre", "Longitud (m)", "Total Cable (m)"]

def _ensure_columns(df: pd.DataFrame, with_del=False) -> pd.DataFrame:
    if df is None or not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(columns=(["__DEL__"] if with_del else []) + COLS_OFICIALES)
    for c in (["__DEL__"] if with_del else []):
        if c not in df.columns:
            df.insert(0, c, False)
    for c in COLS_OFICIALES:
        if c not in df.columns:
            df[c] = pd.Series(dtype="object")
    return df

def _init_state() -> None:
    if "cables_proyecto_df" not in st.session_state:
        st.session_state["cables_proyecto_df"] = pd.DataFrame(columns=COLS_OFICIALES)
    if "cables_buffer_df" not in st.session_state:
        buf = _ensure_columns(st.session_state["cables_proyecto_df"], with_del=True).copy()
        buf["__DEL__"] = False
        st.session_state["cables_buffer_df"] = buf

def _validar_y_calcular(df_in: pd.DataFrame) -> pd.DataFrame:
    cfgs = get_configs_por_tipo()
    cal_por_tipo = get_calibres()

    if "__DEL__" in df_in.columns:
        mask = df_in["__DEL__"].fillna(False)
        if mask.dtype != bool:
            mask = mask.astype(bool, copy=False)
        df_in = df_in[~mask].drop(columns="__DEL__", errors="ignore")

    rows = []
    for _, row in df_in.fillna("").iterrows():
        if not str(row.get("Tipo", "")).strip():
            continue
        tipo = str(row["Tipo"]).strip()

        cfg_ok = cfgs.get(tipo, ["Única"])
        cfg = str(row.get("Configuración") or cfg_ok[0]).strip()
        if cfg not in cfg_ok:
            cfg = cfg_ok[0]

        cal_ok = cal_por_tipo.get(tipo, get_calibres_union())
        cal = str(row.get("Calibre") or (cal_ok[0] if cal_ok else "")).strip()
        if cal_ok and cal not in cal_ok:
            cal = cal_ok[0]

        try:
            L = float(row.get("Longitud (m)", 0) or 0)
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
    st.session_state["cables_proyecto_df"] = df.copy()
    lista = df.to_dict(orient="records")
    st.session_state["cables_proyecto"] = lista
    st.session_state.setdefault("datos_proyecto", {})
    st.session_state["datos_proyecto"]["cables_proyecto"] = lista

def _editor_df_actual() -> pd.DataFrame:
    """
    Devuelve el DF 'real' que el usuario ve en el editor:
    - Si st.session_state['cables_editor'] es DataFrame, lo usa directo.
    - Si es dict de parches (edited_rows/added_rows/deleted_rows), aplica los cambios
      sobre el buffer y devuelve el DF resultante.
    """
    raw = st.session_state.get("cables_editor")
    base = _ensure_columns(st.session_state.get("cables_buffer_df"), with_del=True).copy()

    # Caso 1: ya es un DataFrame (versiones nuevas)
    if isinstance(raw, pd.DataFrame):
        return _ensure_columns(raw, with_del=True).copy()

    # Caso 2: diccionario de parches (versiones anteriores)
    if isinstance(raw, dict):
        df = base.copy()

        # eliminados
        for idx in raw.get("deleted_rows", []):
            if 0 <= idx < len(df):
                df = df.drop(df.index[idx])

        # editados
        for idx, changes in raw.get("edited_rows", {}).items():
            if 0 <= idx < len(df):
                for k, v in changes.items():
                    if k in df.columns:
                        df.iloc[idx, df.columns.get_loc(k)] = v

        # agregados
        for row in raw.get("added_rows", []):
            new = {c: row.get(c, None) for c in df.columns}
            df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)

        df = df.reset_index(drop=True)
        return _ensure_columns(df, with_del=True)

    # Fallback: devolver el buffer
    return base

def _resumen_por_calibre(df: pd.DataFrame) -> str:
    # agrupar por Calibre y sumar total
    if df.empty:
        return "0.00 m"
    g = (df.groupby("Calibre", dropna=True)["Total Cable (m)"]
           .sum()
           .sort_values(ascending=False))
    piezas = [f"{v:,.2f} m de {k}" for k, v in g.items()]
    return " + ".join(piezas)

# ----------------- Sección principal -----------------
def seccion_cables():
    _init_state()

    # Mostrar toasts post-rerun
    if st.session_state.pop("toast_cables_ok", False):
        st.success("✅ Cambios guardados.")
    if st.session_state.pop("toast_cables_reset", False):
        st.info("Cambios descartados.")

    st.markdown("## 2️⃣ ⚡ Configuración y calibres de conductores (tabla)")
    st.caption("Edita el buffer y pulsa **Guardar**. Marca **Eliminar** para borrar filas.")

    with st.form("editor_cables", clear_on_submit=False):
        st.data_editor(
            st.session_state["cables_buffer_df"],
            key="cables_editor",
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_order=["__DEL__", "Tipo", "Configuración", "Calibre", "Longitud (m)", "Total Cable (m)"],
            column_config={
                "__DEL__": st.column_config.CheckboxColumn("Eliminar", width="small",
                                                           help="Marca y pulsa Guardar para borrar"),
                "Tipo": st.column_config.SelectboxColumn("Tipo", options=get_tipos(), required=False, width="small"),
                "Configuración": st.column_config.SelectboxColumn("Configuración", options=get_configs_union(),
                                                                  required=False, width="small"),
                "Calibre": st.column_config.SelectboxColumn("Calibre", options=get_calibres_union(),
                                                            required=False, width="medium"),
                "Longitud (m)": st.column_config.NumberColumn("Longitud (m)", min_value=0.0, step=10.0, format="%.2f"),
                "Total Cable (m)": st.column_config.NumberColumn("Total Cable (m)", disabled=True, format="%.2f",
                                                                 help="Longitud × Nº de conductores"),
            },
        )
        c1, c2 = st.columns([1, 1])
        guardar = c1.form_submit_button("💾 Guardar cambios", type="primary", use_container_width=True)
        descartar = c2.form_submit_button("↩️ Descartar cambios", use_container_width=True)

    if guardar:
        df_editor = _editor_df_actual()                 # <- robusto
        df_validado = _validar_y_calcular(df_editor)    # normaliza y calcula totales
        _persistir_oficial(df_validado)

        # sincr. buffer y limpiar checkboxes
        buf = _ensure_columns(st.session_state["cables_proyecto_df"], with_del=True).copy()
        buf["__DEL__"] = False
        st.session_state["cables_buffer_df"] = buf

        st.session_state["toast_cables_ok"] = True
        st.rerun()

    elif descartar:
        buf = _ensure_columns(st.session_state["cables_proyecto_df"], with_del=True).copy()
        buf["__DEL__"] = False
        st.session_state["cables_buffer_df"] = buf

        st.session_state["toast_cables_reset"] = True
        st.rerun()

    st.markdown("---")

    # Resultados (tabla limpia + resumen por calibre)
    df_out = st.session_state["cables_proyecto_df"].copy()
    if df_out.empty:
        st.info("No hay datos guardados.")
    else:
        df_disp = df_out.reindex(columns=COLS_OFICIALES).copy()
        df_disp.insert(0, "Ítem", range(1, len(df_disp) + 1))

        st.dataframe(
            df_disp,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Ítem": st.column_config.NumberColumn("Ítem", format="%d", width="small"),
                "Longitud (m)": st.column_config.NumberColumn("Longitud (m)", format="%.2f"),
                "Total Cable (m)": st.column_config.NumberColumn("Total Cable (m)", format="%.2f"),
            },
        )

        st.markdown(f"**📏 Total Global de Cable:** {_resumen_por_calibre(df_out)}")

    return st.session_state.get("cables_proyecto", [])
