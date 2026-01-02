# -*- coding: utf-8 -*-
from __future__ import annotations

import streamlit as st
import pandas as pd
from typing import List, Dict, Tuple


# ----------------- Catálogos -----------------
def get_tipos() -> List[str]:
    return ["MT", "BT", "N", "HP", "Retenida"]


def get_calibres() -> Dict[str, List[str]]:
    return {
        "MT": ["2 ACSR", "1/0 ACSR", "2/0 ACSR", "3/0 ACSR", "4/0 ACSR", "266.8 MCM", "336 MCM"],
        "BT": ["2 WP", "1/0 WP", "2/0 WP", "3/0 WP", "4/0 WP"],
        "N":  ["2 ACSR", "1/0 ACSR", "2/0 ACSR", "3/0 ACSR", "4/0 ACSR"],
        "HP": ["2 WP", "1/0 WP", "2/0 WP"],
        "Retenida": ["1/4", "5/8", "3/4"],
    }


def get_configs_por_tipo() -> Dict[str, List[str]]:
    # ✅ BT fases, N neutro, HP piloto en filas separadas con calibres diferentes
    return {
        "MT": ["1F", "2F", "3F"],
        "BT": ["1F", "2F"],
        "N":  ["N"],
        "HP": ["1F"],      # ✅ HP SIEMPRE 1 conductor
        "Retenida": ["Única"],
    }


def get_configs_union() -> List[str]:
    # unión para data_editor, validación al guardar
    return ["Única", "N", "1F", "2F", "3F"]


def get_calibres_union() -> List[str]:
    cal = get_calibres()
    return list(dict.fromkeys(c for lista in cal.values() for c in lista))


def conductores_de(tipo: str, cfg: str) -> int:
    t = (tipo or "").strip().upper()
    c = (cfg or "").strip().upper()

    if t == "MT":
        if c == "1F": return 1
        if c == "2F": return 2
        if c == "3F": return 3
        return 1

    if t == "BT":
        if c == "1F": return 1
        if c == "2F": return 2
        return 1

    if t == "N":
        return 1

    if t == "HP":
        # ✅ Hilo piloto = 1 conductor SIEMPRE
        return 1

    if t == "RETENIDA":
        return 1

    return 1


# ----------------- Estado y helpers -----------------
COLS_OFICIALES = ["Tipo", "Configuración", "Calibre", "Longitud (m)", "Total Cable (m)"]


def _ensure_columns(df: pd.DataFrame, with_del: bool = False) -> pd.DataFrame:
    if df is None or not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(columns=(["__DEL__"] if with_del else []) + COLS_OFICIALES)

    if with_del and "__DEL__" not in df.columns:
        df.insert(0, "__DEL__", False)

    for c in COLS_OFICIALES:
        if c not in df.columns:
            if c in ("Longitud (m)", "Total Cable (m)"):
                df[c] = pd.Series(dtype="float")
            else:
                df[c] = pd.Series(dtype="object")

    return df


def _init_state() -> None:
    if "cables_proyecto_df" not in st.session_state:
        st.session_state["cables_proyecto_df"] = pd.DataFrame(columns=COLS_OFICIALES)

    if "cables_buffer_df" not in st.session_state:
        buf = _ensure_columns(st.session_state["cables_proyecto_df"], with_del=True).copy()
        buf["__DEL__"] = False
        st.session_state["cables_buffer_df"] = buf


def _editor_df_actual() -> pd.DataFrame:
    raw = st.session_state.get("cables_editor")
    base = _ensure_columns(st.session_state.get("cables_buffer_df"), with_del=True).copy()

    if isinstance(raw, pd.DataFrame):
        return _ensure_columns(raw, with_del=True).copy()

    if isinstance(raw, dict):
        df = base.copy()

        for idx in raw.get("deleted_rows", []):
            if 0 <= idx < len(df):
                df = df.drop(df.index[idx])

        for idx, changes in raw.get("edited_rows", {}).items():
            if 0 <= idx < len(df):
                for k, v in changes.items():
                    if k in df.columns:
                        df.iloc[idx, df.columns.get_loc(k)] = v

        for row in raw.get("added_rows", []):
            new = {c: row.get(c, None) for c in df.columns}
            df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)

        return _ensure_columns(df.reset_index(drop=True), with_del=True)

    return base


def _validar_y_calcular(df_in: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    cfgs = get_configs_por_tipo()
    cal_por_tipo = get_calibres()

    # quitar eliminados
    if "__DEL__" in df_in.columns:
        mask = df_in["__DEL__"].fillna(False)
        if mask.dtype != bool:
            mask = mask.astype(bool, copy=False)
        df_in = df_in[~mask].drop(columns="__DEL__", errors="ignore")

    warnings = []
    rows = []

    for i, row in df_in.fillna("").reset_index(drop=True).iterrows():
        tipo = str(row.get("Tipo", "")).strip()
        if not tipo:
            continue

        cfg = str(row.get("Configuración", "")).strip()
        cal = str(row.get("Calibre", "")).strip()

        cfg_ok = cfgs.get(tipo, ["Única"])
        cal_ok = cal_por_tipo.get(tipo, get_calibres_union())

        # defaults
        if not cfg:
            cfg = cfg_ok[0]
        if not cal:
            cal = cal_ok[0] if cal_ok else ""

        # auto-corrección
        if cfg not in cfg_ok:
            warnings.append(
                f"Fila {i+1}: Tipo={tipo} no permite Configuración='{cfg}'. Se ajustó a '{cfg_ok[0]}'."
            )
            cfg = cfg_ok[0]

        if cal_ok and cal not in cal_ok:
            warnings.append(
                f"Fila {i+1}: Tipo={tipo} no permite Calibre='{cal}'. Se ajustó a '{cal_ok[0]}'."
            )
            cal = cal_ok[0]

        try:
            L = float(row.get("Longitud (m)", 0) or 0)
        except Exception:
            L = 0.0

        ncond = conductores_de(tipo, cfg)
        total = L * ncond

        rows.append({
            "Tipo": tipo,
            "Configuración": cfg,
            "Calibre": cal,
            "Longitud (m)": float(L),
            "Total Cable (m)": float(total),
        })

    df_out = pd.DataFrame(rows, columns=COLS_OFICIALES)
    return df_out, warnings


def _persistir_oficial(df: pd.DataFrame) -> None:
    st.session_state["cables_proyecto_df"] = df.copy()
    lista = df.to_dict(orient="records")
    st.session_state["cables_proyecto"] = lista
    st.session_state.setdefault("datos_proyecto", {})
    st.session_state["datos_proyecto"]["cables_proyecto"] = lista


def _resumen_por_calibre(df: pd.DataFrame) -> str:
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

    if st.session_state.pop("toast_cables_ok", False):
        st.success("✅ Cambios guardados.")
    if st.session_state.pop("toast_cables_reset", False):
        st.info("Cambios descartados.")

    st.markdown("## 2️⃣ ⚡ Configuración y calibres de conductores (tabla)")
    st.caption(
        "✅ Tu lógica: **BT (fases)**, **N (neutro)** y **HP (hilo piloto)** van en **filas separadas** "
        "para permitir **calibres diferentes**."
    )

    with st.form("editor_cables", clear_on_submit=False):
        st.data_editor(
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
                    help="Longitud × Nº de conductores (HP siempre 1)"
                ),
            },
        )
        c1, c2 = st.columns([1, 1])
        guardar = c1.form_submit_button("💾 Guardar cambios", type="primary", use_container_width=True)
        descartar = c2.form_submit_button("↩️ Descartar cambios", use_container_width=True)

    if guardar:
        df_editor = _editor_df_actual()
        df_validado, warnings = _validar_y_calcular(df_editor)

        if warnings:
            st.warning("Se ajustaron combinaciones inválidas automáticamente:")
            for w in warnings:
                st.write("• " + w)

        _persistir_oficial(df_validado)

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


# =========================
# Soporte para PDFs (usado por modulo.pdf_utils)
# =========================
def tabla_cables_pdf(datos_proyecto):
    elems = []
    try:
        from reportlab.platypus import Paragraph, Table, TableStyle, Spacer
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
    except Exception:
        return elems

    fuente = None
    if isinstance(st.session_state.get("cables_proyecto"), list) and st.session_state["cables_proyecto"]:
        fuente = st.session_state["cables_proyecto"]
    elif isinstance(st.session_state.get("cables_proyecto_df"), pd.DataFrame) and not st.session_state["cables_proyecto_df"].empty:
        fuente = st.session_state["cables_proyecto_df"].to_dict(orient="records")
    else:
        lista_dp = (datos_proyecto or {}).get("cables_proyecto", [])
        if isinstance(lista_dp, list) and lista_dp:
            fuente = lista_dp

    if not fuente:
        return elems

    df = pd.DataFrame(fuente).copy()

    colmap = {
        "Tipo": "Tipo",
        "Configuración": "Configuración",
        "Calibre": "Calibre",
        "Longitud (m)": "Longitud (m)",
        "Total Cable (m)": "Total Cable (m)",
        "Longitud": "Longitud (m)",
        "Total": "Total Cable (m)",
    }
    df.rename(columns={c: colmap[c] for c in list(df.columns) if c in colmap}, inplace=True)

    cols = ["Tipo", "Configuración", "Calibre", "Longitud (m)", "Total Cable (m)"]
    for c in cols:
        if c not in df.columns:
            df[c] = "" if c in ("Tipo", "Configuración", "Calibre") else 0.0

    df = df[cols].copy()
    for c in ("Longitud (m)", "Total Cable (m)"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    styles = getSampleStyleSheet()
    styleH = styles["Heading2"]
    styleN = styles["Normal"]

    elems.append(Spacer(1, 0.20 * inch))
    elems.append(Paragraph("⚡ Configuración y Calibres de Conductores", styleH))
    elems.append(Spacer(1, 0.10 * inch))

    data = [["Tipo", "Configuración", "Calibre", "Longitud (m)", "Total Cable (m)"]]
    for _, row in df.iterrows():
        data.append([
            str(row["Tipo"]),
            str(row["Configuración"]),
            str(row["Calibre"]),
            f"{float(row['Longitud (m)']):.2f}",
            f"{float(row['Total Cable (m)']):.2f}",
        ])

    tabla = Table(data, colWidths=[1.1 * inch, 1.2 * inch, 1.6 * inch, 1.2 * inch, 1.5 * inch])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
    ]))
    elems.append(tabla)

    total_global = float(df["Total Cable (m)"].sum())
    elems.append(Spacer(1, 0.15 * inch))
    elems.append(Paragraph(f"🧮 <b>Total Global de Cable:</b> {total_global:,.2f} m", styleN))
    elems.append(Spacer(1, 0.20 * inch))

    return elems
