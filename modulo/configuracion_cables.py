# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import streamlit as st
import pandas as pd
from typing import List, Dict, Tuple


# =========================
# Catálogo oficial (TU LISTA)
# =========================
CABLES_OFICIALES = {
    # Retenidas (acerado)
    ("RETENIDA", "1/4"):  'Cable Acerado 1/4"',
    ("RETENIDA", "5/16"): 'Cable Acerado 5/16"',
    ("RETENIDA", "3/8"):  'Cable Acerado 3/8"',

    # BT forrado WP (Quince/Fig/Peach)
    ("BT", "2 WP"):     "Cable de Aluminio Forrado WP # 2 AWG Peach",
    ("BT", "1/0 WP"):   "Cable de Aluminio Forrado WP # 1/0 AWG Quince",
    ("BT", "3/0 WP"):   "Cable de Aluminio Forrado WP # 3/0 AWG Fig",
    ("BT", "266.8 MCM"): "Cable de Aluminio Forrado 266.8 MCM Mulberry",

    # HP Hilo Piloto
    ("HP", "2 WP"):   "Cable de Aluminio Forrado WP # 2 AWG Peach",
    ("HP", "1/0 WP"): "Cable de Aluminio Forrado WP # 1/0 AWG Quince",

    # Neutro (ACSR)
    ("N", "2 ACSR"):    "Cable de Aluminio ACSR # 2 AWG Sparrow",
    ("N", "1/0 ACSR"):  "Cable de Aluminio ACSR # 1/0 AWG Raven",
    ("N", "2/0 ACSR"):  "Cable de Aluminio ACSR # 2/0 AWG Quail",
    ("N", "3/0 ACSR"):  "Cable de Aluminio ACSR # 3/0 AWG Pigeon",
    ("N", "4/0 ACSR"):  "Cable de Aluminio ACSR # 4/0 AWG Penguin",

    # Media Tensión
    ("MT", "1/0 ACSR"):   "Cable de Aluminio ACSR # 1/0 AWG Raven",
    ("MT", "2/0 ACSR"):   "Cable de Aluminio ACSR # 2/0 AWG Quail",
    ("MT", "3/0 ACSR"):   "Cable de Aluminio ACSR # 3/0 AWG Pigeon",
    ("MT", "4/0 ACSR"):   "Cable de Aluminio ACSR # 4/0 AWG Penguin",
    ("MT", "266.8 MCM"):  "Cable de Aluminio ACSR # 266.8 MCM Partridge",
    ("MT", "477 MCM"):    "Cable de Aluminio ACSR # 477 MCM Flicker",
    ("MT", "556 MCM ACSR"): "Cable de Aluminio ACSR # 556 MCM Dove",
    ("MT", "556 MCM AAC"):  "Cable de Aluminio AAC # 556 MCM Dahlia",
}

# ========= Helpers de normalización y mapeo =========
def _norm_txt(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)  # quita dobles espacios
    return s

def _norm_key(s: str) -> str:
    return _norm_txt(s).upper()

# Mapeo inverso: descripción oficial -> calibre corto
DESC_A_CAL = {}
for (tipo, cal), desc in CABLES_OFICIALES.items():
    DESC_A_CAL[(_norm_key(tipo), _norm_key(desc))] = cal

def calibre_corto_desde_seleccion(tipo: str, cal_o_desc: str) -> str:
    """
    Si el usuario selecciona una descripción oficial, la convierte a calibre corto.
    Si ya viene corto, la deja igual.
    """
    t = _norm_key(tipo)
    v = _norm_key(cal_o_desc)
    return DESC_A_CAL.get((t, v), cal_o_desc)

def descripcion_oficial(tipo: str, calibre_corto: str, cal_original: str) -> str:
    """
    Devuelve la descripción oficial del catálogo si existe.
    - Si el usuario eligió descripción, respétala.
    - Si eligió calibre corto, busca el oficial por (tipo, calibre).
    """
    t = (tipo or "").strip().upper()
    # si parece descripción oficial (coincide exacto con alguna del catálogo), usarla
    for (tt, _cal), desc in CABLES_OFICIALES.items():
        if _norm_key(tt) == _norm_key(t) and _norm_key(desc) == _norm_key(cal_original):
            return _norm_txt(desc)

    # si no, buscar por calibre corto
    key = (t, (calibre_corto or "").strip())
    return _norm_txt(CABLES_OFICIALES.get(key, cal_original))


# ----------------- Catálogos para UI -----------------
def get_tipos() -> List[str]:
    return ["MT", "BT", "N", "HP", "Retenida"]


def get_calibres() -> Dict[str, List[str]]:
    return {
        "MT": [
            CABLES_OFICIALES[("MT", "1/0 ACSR")],
            CABLES_OFICIALES[("MT", "2/0 ACSR")],
            CABLES_OFICIALES[("MT", "3/0 ACSR")],
            CABLES_OFICIALES[("MT", "4/0 ACSR")],
            CABLES_OFICIALES[("MT", "266.8 MCM")],
            CABLES_OFICIALES[("MT", "477 MCM")],
            CABLES_OFICIALES[("MT", "556 MCM ACSR")],
            CABLES_OFICIALES[("MT", "556 MCM AAC")],
        ],

        "BT": [
            CABLES_OFICIALES[("BT", "2 WP")],
            CABLES_OFICIALES[("BT", "1/0 WP")],
            CABLES_OFICIALES[("BT", "3/0 WP")],
            CABLES_OFICIALES[("BT", "266.8 MCM")],
        ],

        "N": [
            CABLES_OFICIALES[("N", "2 ACSR")],
            CABLES_OFICIALES[("N", "1/0 ACSR")],
            CABLES_OFICIALES[("N", "2/0 ACSR")],
            CABLES_OFICIALES[("N", "3/0 ACSR")],
            CABLES_OFICIALES[("N", "4/0 ACSR")],
        ],

        "HP": [
            CABLES_OFICIALES[("HP", "2 WP")],
            CABLES_OFICIALES[("HP", "1/0 WP")],
        ],

        "Retenida": [
            CABLES_OFICIALES[("RETENIDA", "1/4")],
            CABLES_OFICIALES[("RETENIDA", "5/16")],
            CABLES_OFICIALES[("RETENIDA", "3/8")],
        ],
    }

def get_configs_por_tipo() -> Dict[str, List[str]]:
    return {
        "MT": ["1F", "2F", "3F"],
        "BT": ["1F", "2F"],
        "N":  ["N"],
        "HP": ["1F", "2F"],
        "Retenida": ["Única"],
    }


def get_configs_union() -> List[str]:
    return ["Única", "N", "1F", "2F", "3F"]


def get_calibres_union() -> List[str]:
    cal = get_calibres()
    return list(dict.fromkeys(c for lista in cal.values() for c in lista))


def conductores_de(tipo: str, cfg: str) -> int:
    t = (tipo or "").strip().upper()
    c = (cfg or "").strip().upper()

    # Si no hay configuración, que "se note" (0 conductores)
    if not c:
        return 0

    if t == "MT":
        if c == "1F": return 1
        if c == "2F": return 2
        if c == "3F": return 3
        return 0  # <- inválida

    if t == "BT":
        if c == "1F": return 1
        if c == "2F": return 2
        return 0

    if t == "N":
        # para neutro normalmente esperás "N"
        return 1 if c == "N" else 0

    if t == "HP":
        if c == "1F": return 1
        if c == "2F": return 2
        return 0

    if t == "RETENIDA":
        # normalmente "Única"
        return 1 if c == "ÚNICA" else 0

    return 0



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


def _validar_y_calcular(df_in: pd.DataFrame) -> Tuple[pd.DataFrame, List[str], List[str]]:
    cfgs = get_configs_por_tipo()
    cal_por_tipo = get_calibres()

    if "__DEL__" in df_in.columns:
        mask = df_in["__DEL__"].fillna(False)
        if mask.dtype != bool:
            mask = mask.astype(bool, copy=False)
        df_in = df_in[~mask].drop(columns="__DEL__", errors="ignore")

    warnings: List[str] = []
    errors: List[str] = []
    rows = []

    for i, row in df_in.fillna("").reset_index(drop=True).iterrows():
        tipo = str(row.get("Tipo", "")).strip()
        if not tipo:
            continue

        cfg = str(row.get("Configuración", "")).strip()
        cal_sel = str(row.get("Calibre", "")).strip()  # descripción oficial
        cfg_ok = cfgs.get(tipo, [])
        cal_ok = cal_por_tipo.get(tipo, get_calibres_union())

        # -------------------------
        # VALIDACIONES "sin defaults"
        # -------------------------
        if not cfg:
            errors.append(f"Fila {i+1}: Falta Configuración para Tipo={tipo}.")
        elif cfg_ok and cfg not in cfg_ok:
            errors.append(f"Fila {i+1}: Configuración inválida '{cfg}' para Tipo={tipo}.")
            cfg = ""  # que quede vacío para que se note

        if not cal_sel:
            errors.append(f"Fila {i+1}: Falta Calibre para Tipo={tipo}.")
        elif cal_ok and cal_sel not in cal_ok:
            errors.append(f"Fila {i+1}: Calibre inválido '{cal_sel}' para Tipo={tipo}.")
            cal_sel = ""  # que quede vacío para que se note

        # Longitud
        try:
            L = float(row.get("Longitud (m)", 0) or 0)
        except Exception:
            L = 0.0
            warnings.append(f"Fila {i+1}: Longitud inválida. Se tomó 0.00 m.")

        # Conductores y total (si cfg vacío => 0)
        ncond = conductores_de(tipo, cfg)
        if cfg and ncond == 0:
            errors.append(f"Fila {i+1}: No se pudo determinar Nº conductores (Tipo={tipo}, Config={cfg}).")

        total = float(L) * float(ncond)

        # Convertir selección a "corto" (si cal_sel vacío, quedará vacío y no pasa nada)
        cal_corto = calibre_corto_desde_seleccion(tipo, cal_sel) if cal_sel else ""

        rows.append({
            "Tipo": tipo,
            "Configuración": cfg,
            "Calibre": cal_sel,
            "Longitud (m)": float(L),
            "Total Cable (m)": float(total),
            "DescripcionMaterial": descripcion_oficial(tipo, cal_corto, cal_sel) if cal_sel else "",
            "CalibreCorto": cal_corto,
        })

    df_out = pd.DataFrame(rows)
    return df_out, warnings, errors


def _persistir_oficial(df: pd.DataFrame) -> None:
    st.session_state["cables_proyecto_df"] = df.copy()
    lista = df.to_dict(orient="records")
    st.session_state["cables_proyecto"] = lista
    st.session_state.setdefault("datos_proyecto", {})
    st.session_state["datos_proyecto"]["cables_proyecto"] = lista


def _resumen_por_calibre(df: pd.DataFrame) -> str:
    if df.empty:
        return "0.00 m"
    g = (df.groupby("Calibre", dropna=True)["Total Cable (m)"].sum().sort_values(ascending=False))
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
                    "Eliminar", width="small", help="Marca y pulsa Guardar para borrar"
                ),
                "Tipo": st.column_config.SelectboxColumn(
                    "Tipo", options=get_tipos(), required=False, width="small"
                ),
                "Configuración": st.column_config.SelectboxColumn(
                    "Configuración", options=get_configs_union(), required=False, width="small"
                ),
                "Calibre": st.column_config.SelectboxColumn(
                    "Calibre", options=get_calibres_union(), required=False, width="large"
                ),
                "Longitud (m)": st.column_config.NumberColumn(
                    "Longitud (m)", min_value=0.0, step=10.0, format="%.2f"
                ),
                "Total Cable (m)": st.column_config.NumberColumn(
                    "Total Cable (m)",
                    disabled=True,
                    format="%.2f",
                    help="Longitud × Nº de conductores (si Configuración está vacía o inválida, Total será 0)",
                ),
            },
        )
        c1, c2 = st.columns([1, 1])
        guardar = c1.form_submit_button("💾 Guardar cambios", type="primary", use_container_width=True)
        descartar = c2.form_submit_button("↩️ Descartar cambios", use_container_width=True)

    # ----------------- Acciones -----------------
    if guardar:
        df_editor = _editor_df_actual()

        # ✅ OJO: ahora _validar_y_calcular debe devolver (df, warnings, errors)
        df_validado, warnings, errors = _validar_y_calcular(df_editor)

        if warnings:
            st.warning("Avisos:")
            for w in warnings:
                st.write("• " + w)

        if errors:
            st.error("❌ No se guardó porque faltan datos o hay valores inválidos:")
            for e in errors:
                st.write("• " + e)
        else:
            _persistir_oficial(df_validado)

            # refrescar buffer desde oficial
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

    # ----------------- Vista de guardado -----------------
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
        import streamlit as st
        import pandas as pd
        from reportlab.platypus import Paragraph, Table, TableStyle, Spacer
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.units import inch
        from xml.sax.saxutils import escape
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

    # ✅ estilos con wrap
    st_hdr = ParagraphStyle(
        "hdr_cables",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=10,
        alignment=TA_CENTER,
        textColor=colors.whitesmoke,
    )

    st_cell = ParagraphStyle(
        "cell_cables",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=9,
        alignment=TA_CENTER,
        wordWrap="CJK",
    )
    st_cell.splitLongWords = 1

    st_cell_left = ParagraphStyle(
        "cell_cables_left",
        parent=st_cell,
        alignment=0,  # TA_LEFT sin importar enums
    )

    elems.append(Spacer(1, 0.20 * inch))
    elems.append(Paragraph("⚡ Configuración y Calibres de Conductores", styleH))
    elems.append(Spacer(1, 0.10 * inch))

    data = [[
        Paragraph("Tipo", st_hdr),
        Paragraph("Configuración", st_hdr),
        Paragraph("Calibre", st_hdr),
        Paragraph("Longitud (m)", st_hdr),
        Paragraph("Total Cable (m)", st_hdr),
    ]]

    for _, row in df.iterrows():
        tipo = escape(str(row["Tipo"]).strip())
        conf = escape(str(row["Configuración"]).strip())
        cal  = escape(str(row["Calibre"]).strip())

        data.append([
            Paragraph(tipo, st_cell),
            Paragraph(conf, st_cell),
            Paragraph(cal, st_cell_left),  # ✅ calibre suele ser largo: mejor alinearlo a la izquierda
            Paragraph(f"{float(row['Longitud (m)']):.2f}", st_cell),
            Paragraph(f"{float(row['Total Cable (m)']):.2f}", st_cell),
        ])

    tabla = Table(
        data,
        colWidths=[1.0 * inch, 1.0 * inch, 2.4 * inch, 1.0 * inch, 1.3 * inch],
        repeatRows=1
    )

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),

        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),

        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 3),

        # ✅ wrap fuerte en Calibre
        ("WORDWRAP", (2, 1), (2, -1), "CJK"),
    ]))

    elems.append(tabla)

    total_global = float(df["Total Cable (m)"].sum())
    elems.append(Spacer(1, 0.15 * inch))
    elems.append(Paragraph(f"🧮 <b>Total Global de Cable:</b> {total_global:,.2f} m", styleN))
    elems.append(Spacer(1, 0.20 * inch))

    return elems

    return elems
