# -*- coding: utf-8 -*-
"""
modulo/configuracion_cables.py

Sección Cables:
- Editor estable con Guardar/Descartar y columna Eliminar.
- Sin fila "semilla": el editor inicia vacío (usa + para agregar).
- Validación por Tipo: configura Calibre/Configuración válidos y calcula Total Cable.
- Tabla final limpia sin índice y con columna Ítem (1..n).
- Resumen por calibre: "2,000 m de 1/0 ASCR + ...", y para Retenida: "cable acerado <calibre>".

Datos oficiales:
  st.session_state['cables_proyecto_df']                 -> DataFrame oficial
  st.session_state['cables_proyecto']                    -> lista de dicts oficial
  st.session_state['datos_proyecto']['cables_proyecto']  -> espejo para otros módulos
"""

from __future__ import annotations
from typing import List, Dict

import streamlit as st
import pandas as pd

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

def _ensure_columns(df: pd.DataFrame, with_del: bool = False) -> pd.DataFrame:
    """Asegura columnas en el orden esperado (opcionalmente con __DEL__)."""
    cols = (["__DEL__"] + COLS_OFICIALES) if with_del else COLS_OFICIALES
    base = {c: [] for c in cols}
    out = pd.DataFrame(base)
    if df is None or df.empty:
        return out
    df2 = df.copy()
    # agrega faltantes
    for c in cols:
        if c not in df2.columns:
            df2[c] = False if c == "__DEL__" else (0.0 if c in ("Longitud (m)", "Total Cable (m)") else "")
    # ordena
    return df2[cols]

def _init_state() -> None:
    """Crea data oficial y buffer de edición sin fila semilla."""
    if "cables_proyecto_df" not in st.session_state:
        st.session_state["cables_proyecto_df"] = pd.DataFrame(columns=COLS_OFICIALES)

    # Buffer de edición (con columna Eliminar), sin sembrar una fila por defecto
    if "cables_buffer_df" not in st.session_state:
        buf = st.session_state["cables_proyecto_df"].copy()
        buf = _ensure_columns(buf, with_del=True)
        st.session_state["cables_buffer_df"] = buf

def _validar_y_calcular(df_in: pd.DataFrame) -> pd.DataFrame:
    """Normaliza por tipo y calcula total; respeta borrados del checkbox."""
    cfgs = get_configs_por_tipo()
    cal_por_tipo = get_calibres()

    # Borrar filas marcadas (dtype seguro)
    df_in = _ensure_columns(df_in, with_del=True)
    mask = df_in["__DEL__"].fillna(False)
    if mask.dtype != bool:
        mask = mask.astype(bool, copy=False)
    df_in = df_in[~mask].drop(columns="__DEL__", errors="ignore")

    rows = []
    for _, row in df_in.fillna("").iterrows():
        if not str(row.get("Tipo", "")).strip():
            continue  # ignora filas vacías

        tipo = str(row["Tipo"]).strip()

        # Configuración permitida por tipo
        cfg_ok = cfgs.get(tipo, ["Única"])
        cfg = str(row.get("Configuración") or cfg_ok[0]).strip()
        if cfg not in cfg_ok:
            cfg = cfg_ok[0]

        # Calibre permitido por tipo
        cal_ok = cal_por_tipo.get(tipo, get_calibres_union())
        cal = str(row.get("Calibre") or (cal_ok[0] if cal_ok else "")).strip()
        if cal_ok and cal not in cal_ok:
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
    df_ok = _ensure_columns(df, with_del=False)
    st.session_state["cables_proyecto_df"] = df_ok.copy()
    lista = df_ok.to_dict(orient="records")
    st.session_state["cables_proyecto"] = lista
    st.session_state.setdefault("datos_proyecto", {})
    st.session_state["datos_proyecto"]["cables_proyecto"] = lista

# --- Helpers para resumen por calibre ---
def _fmt_metros(v: float) -> str:
    if abs(v - round(v)) < 1e-9:
        return f"{int(round(v)):,.0f} m"
    return f"{v:,.2f} m"

def _resumen_por_calibre(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return _fmt_metros(0)
    tmp = df.copy()

    # Etiqueta amigable: Retenida => "cable acerado <calibre>", otros => solo calibre
    tmp["Etiqueta"] = tmp.apply(
        lambda r: (f"cable acerado {str(r.get('Calibre','')).strip()}"
                   if str(r.get("Tipo","")).strip().upper() == "RETENIDA"
                   else str(r.get("Calibre","")).strip()),
        axis=1
    )

    totales = (tmp.groupby("Etiqueta", dropna=True)["Total Cable (m)"]
                 .sum()
                 .sort_values(ascending=False))

    partes = [f"{_fmt_metros(m)} de {et}" for et, m in totales.items() if m > 0]
    return " + ".join(partes) if partes else _fmt_metros(0)


# =========================
# Sección principal
# =========================
def seccion_cables():
    _init_state()

    # ---------- TÍTULO ----------
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
                    "Tipo", options=get_tipos(), required=False, width="small"
                ),
                "Configuración": st.column_config.SelectboxColumn(
                    "Configuración", options=get_configs_union(), required=False, width="small"
                ),
                "Calibre": st.column_config.SelectboxColumn(
                    "Calibre", options=get_calibres_union(), required=False, width="medium"
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

        # Sincroniza buffer con oficial (incluye __DEL__ desmarcado)
        buf = _ensure_columns(st.session_state["cables_proyecto_df"], with_del=True)
        buf["__DEL__"] = False
        st.session_state["cables_buffer_df"] = buf
        st.success("✅ Cambios guardados.")

    elif descartar:
        buf = _ensure_columns(st.session_state["cables_proyecto_df"], with_del=True)
        buf["__DEL__"] = False
        st.session_state["cables_buffer_df"] = buf
        st.info("Cambios descartados.")

    st.markdown("---")

    # ---------- RESULTADOS (tabla limpia + resumen por calibre) ----------
    df_out = st.session_state["cables_proyecto_df"].copy()
    if df_out.empty:
        st.info("No hay datos guardados.")
    else:
        df_disp = df_out.reindex(columns=COLS_OFICIALES).copy()
        df_disp.insert(0, "Ítem", range(1, len(df_disp) + 1))

        # Tabla final limpia SIN índice real
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

        # Resumen por calibre
        st.markdown(f"**📏 Total Global de Cable:** {_resumen_por_calibre(df_out)}")

    # Devuelve lista (API histórica de tu app)
    return st.session_state.get("cables_proyecto", [])

