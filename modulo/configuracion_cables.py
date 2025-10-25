# -*- coding: utf-8 -*-
"""
modulo/configuracion_cables.py

Sección Cables (UX pulida):
- Editor (buffer) arriba con columna "Eliminar".
- Guardar valida por tipo, calcula total y persiste.
- Descartar regresa el buffer a lo oficial.
- Si el editor está vacío pero hay datos guardados -> se rellena con lo oficial.
- KPIs + tabla limpia de resultados con columna Ítem (1..n) sin índice.

Estado:
  st.session_state['cables_proyecto_df']  -> DataFrame oficial
  st.session_state['cables_proyecto']     -> lista(dicts) oficial
  st.session_state['cables_buffer_df']    -> DataFrame del editor (con __DEL__)
  st.session_state['datos_proyecto']['cables_proyecto'] -> espejo para otros módulos
"""

from __future__ import annotations

from typing import Dict, List
import pandas as pd
import streamlit as st

# ---------------------------
# Catálogos
# ---------------------------
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
    # dedup preservando orden
    return list(dict.fromkeys(c for grupo in cal.values() for c in grupo))

def conductores_de(cfg: str) -> int:
    c = (cfg or "").strip().upper()
    if c in ("ÚNICA", "N", "1F"): return 1
    if c in ("1F+N", "2F"):       return 2
    if c in ("3F", "2F+N"):       return 3
    if c == "2F+HP+N":            return 4
    return 1


# ---------------------------
# Estado y utilitarios
# ---------------------------
COLS_OFICIALES = ["Tipo", "Configuración", "Calibre", "Longitud (m)", "Total Cable (m)"]

def _init_state() -> None:
    """Crea estructuras base sin filas ‘guía’."""
    if "cables_proyecto_df" not in st.session_state:
        st.session_state["cables_proyecto_df"] = pd.DataFrame(columns=COLS_OFICIALES)

    if "cables_buffer_df" not in st.session_state:
        ofi = st.session_state["cables_proyecto_df"].copy()
        buf = ofi if not ofi.empty else pd.DataFrame(columns=COLS_OFICIALES)
        if "__DEL__" not in buf.columns:
            buf.insert(0, "__DEL__", False)
        st.session_state["cables_buffer_df"] = buf

def _validar_y_calcular(df_in: pd.DataFrame) -> pd.DataFrame:
    """Normaliza por tipo, asegura opciones válidas y calcula ‘Total Cable (m)’."""
    cfgs = get_configs_por_tipo()
    cal_por_tipo = get_calibres()

    # Eliminar filas marcadas
    if "__DEL__" in df_in.columns:
        mask = df_in["__DEL__"].fillna(False)
        if mask.dtype is not bool:
            mask = mask.astype(bool, copy=False)
        df_in = df_in[~mask].drop(columns="__DEL__", errors="ignore")

    rows = []
    for _, row in df_in.fillna("").iterrows():
        if not row.get("Tipo"):
            continue

        tipo = str(row["Tipo"]).strip()

        cfg_ok = cfgs.get(tipo, ["Única"])
        cfg = str(row.get("Configuración") or cfg_ok[0])
        if cfg not in cfg_ok:
            cfg = cfg_ok[0]

        cal_ok = cal_por_tipo.get(tipo, get_calibres_union())
        cal = str(row.get("Calibre") or (cal_ok[0] if cal_ok else ""))
        if cal_ok and cal not in cal_ok:
            cal = cal_ok[0]

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


# ---------------------------
# UI principal
# ---------------------------
def seccion_cables():
    _init_state()

    st.markdown("## 2️⃣ ⚡ Configuración y calibres de conductores (tabla)")
    st.caption("Edita el buffer y pulsa **Guardar**. Marca **Eliminar** para borrar filas.")

    # --- Editor (buffer) ---
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
                    "Eliminar", help="Marca y pulsa Guardar para borrar", width="small"
                ),
                "Tipo": st.column_config.SelectboxColumn("Tipo", options=get_tipos(), required=True, width="small"),
                "Configuración": st.column_config.SelectboxColumn(
                    "Configuración", options=get_configs_union(), required=True, width="small"
                ),
                "Calibre": st.column_config.SelectboxColumn(
                    "Calibre", options=get_calibres_union(), required=True, width="medium"
                ),
                "Longitud (m)": st.column_config.NumberColumn("Longitud (m)", min_value=0.0, step=10.0, format="%.2f"),
                "Total Cable (m)": st.column_config.NumberColumn("Total Cable (m)", disabled=True, format="%.2f"),
            },
        )
        c1, c2 = st.columns([1, 1])
        guardar = c1.form_submit_button("💾 Guardar cambios", type="primary", use_container_width=True)
        descartar = c2.form_submit_button("↩️ Descartar cambios", use_container_width=True)

    # --- Acciones ---
    if guardar:
        df_ok = _validar_y_calcular(edited)
        _persistir_oficial(df_ok)

        # reconstruir buffer desde oficial
        buf = df_ok.copy()
        if "__DEL__" not in buf.columns:
            buf.insert(0, "__DEL__", False)
        st.session_state["cables_buffer_df"] = buf
        st.success("✅ Cambios guardados.")

    elif descartar:
        ofi = st.session_state["cables_proyecto_df"].copy()
        if "__DEL__" not in ofi.columns:
            ofi.insert(0, "__DEL__", False)
        st.session_state["cables_buffer_df"] = ofi
        st.info("Cambios descartados.")

    # 🔁 Re-poblar editor si quedó vacío pero hay datos guardados
    if st.session_state["cables_buffer_df"].empty and not st.session_state["cables_proyecto_df"].empty:
        ofi = st.session_state["cables_proyecto_df"].copy()
        if "__DEL__" not in ofi.columns:
            ofi.insert(0, "__DEL__", False)
        st.session_state["cables_buffer_df"] = ofi

    st.markdown("---")

    # --- Resultados (solo lectura) ---
    df_out = st.session_state["cables_proyecto_df"].copy()
    if df_out.empty:
        st.info("No hay datos guardados.")
    else:
        # SIN KPIs: solo tabla limpia + total global
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
        # --- Helpers para el resumen por calibre ---
def _fmt_metros(v: float) -> str:
    # sin decimales si es entero, sino 2 decimales
    if abs(v - round(v)) < 1e-9:
        return f"{int(round(v)):,.0f} m"
    return f"{v:,.2f} m"

def _resumen_por_calibre(df: pd.DataFrame) -> str:
    # Etiqueta amigable: para Retenida muestra "cable acerado 1/4", demás solo el calibre
    etiquetas = df.apply(
        lambda r: (f"cable acerado {r['Calibre']}" if str(r.get('Tipo','')).strip().upper() == "RETENIDA"
                   else str(r['Calibre']).strip()),
        axis=1
    )
    tmp = df.copy()
    tmp["Etiqueta"] = etiquetas

    # Sumar por etiqueta
    totales = (tmp.groupby("Etiqueta", dropna=True)["Total Cable (m)"]
                 .sum()
                 .sort_values(ascending=False))

    # Armar la frase: "2,000 m de <Etiqueta> + ..."
    partes = [f"{_fmt_metros(m)} de {et}" for et, m in totales.items() if m > 0]
    return " + ".join(partes) if partes else _fmt_metros(0)

# ... dentro de tu seccion_cables(), reemplaza el total simple por esto:
if not df_out.empty:
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

    # ⬇️ Nuevo resumen por calibre
    resumen = _resumen_por_calibre(df_out)
    st.markdown(f"**📏 Total Global de Cable:** {resumen}")


    return st.session_state.get("cables_proyecto", [])


