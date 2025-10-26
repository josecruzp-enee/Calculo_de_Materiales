# interfaz/estructuras.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import os
import re
import time
import tempfile
from typing import Tuple, List, Dict, Optional

import numpy as np
import pandas as pd
import streamlit as st


# ==============================================================================
# CONFIG BASE
# ==============================================================================
COLUMNAS_BASE: List[str] = [
    "Punto",
    "Poste",
    "Primario",
    "Secundario",
    "Retenidas",
    "Conexiones a tierra",
    "Transformadores",
]

CAT_COLS: List[str] = COLUMNAS_BASE[1:]


# ==============================================================================
# PARSEO Y NORMALIZACIÓN
# ==============================================================================
def _normalizar_columnas(df: pd.DataFrame, columnas: List[str]) -> pd.DataFrame:
    df = df.rename(columns={
        "Retenida": "Retenidas",
        "Aterrizaje": "Conexiones a tierra",
        "Transformador": "Transformadores",
    })
    for c in columnas:
        if c not in df.columns:
            df[c] = ""
    return df[columnas]


def _limpiar_codigo(s: str) -> str:
    if pd.isna(s): return ""
    s = str(s).strip()
    return re.sub(r"\s*\([^)]*\)\s*$", "", s).strip()


def _split(cell) -> List[str]:
    if not isinstance(cell, str): cell = str(cell or "")
    if cell.strip() in ("", "-"): return []
    return [x.strip() for x in re.split(r"[,;\n\r]+", cell) if x.strip()]


def _parse_item(piece: str) -> Tuple[str, int]:
    # 2x CODE
    m = re.match(r"^(\d+)\s*[x×]\s*(.+)$", piece, flags=re.I)
    if m: return _limpiar_codigo(m.group(2)), int(m.group(1))
    # 2 CODE
    m = re.match(r"^(\d+)\s+(.+)$", piece)
    if m: return _limpiar_codigo(m.group(2)), int(m.group(1))
    # 2CODE
    m = re.match(r"^(\d+)([A-Za-z].+)$", piece)
    if m: return _limpiar_codigo(m.group(2)), int(m.group(1))
    return _limpiar_codigo(piece), 1


def ancho_a_largo(df_ancho: pd.DataFrame) -> pd.DataFrame:
    rows = []
    df = _normalizar_columnas(df_ancho, COLUMNAS_BASE)
    for _, r in df.iterrows():
        punto = str(r.get("Punto", "")).strip()
        for col in CAT_COLS:
            piezas = _split(r.get(col, ""))
            for p in piezas:
                code, qty = _parse_item(p)
                if code:
                    rows.append({"Punto": punto,
                                 "codigodeestructura": code,
                                 "cantidad": int(qty)})
    return pd.DataFrame(rows, columns=["Punto", "codigodeestructura", "cantidad"])


# ==============================================================================
# SANITIZACIÓN FINAL 1-D (Evita error en exportación.py)
# ==============================================================================
def _scalarize(v) -> str:
    if isinstance(v, (list, tuple, set)):
        return ", ".join(map(str, v))
    if isinstance(v, np.ndarray):
        return ", ".join(map(str, v.tolist()))
    if v is None:
        return ""
    return str(v)


def sanitizar(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["Punto", "codigodeestructura", "cantidad"])

    df = df.copy()

    # columnas mínimas
    for c in ["Punto", "codigodeestructura", "cantidad"]:
        if c not in df.columns:
            df[c] = "" if c != "cantidad" else 0

    df["Punto"] = df["Punto"].map(_scalarize).fillna("").astype(str)
    df["codigodeestructura"] = df["codigodeestructura"].map(_scalarize).fillna("").astype(str)
    df["codigodeestructura"] = df["codigodeestructura"].map(_limpiar_codigo)

    # cantidad int segura
    df["cantidad"] = df["cantidad"].apply(lambda x: int(float(x)) if str(x).replace(".", "", 1).isdigit() else 0)

    df = df[(df["codigodeestructura"] != "") & (df["cantidad"] > 0)]
    return df[["Punto", "codigodeestructura", "cantidad"]].reset_index(drop=True)


# ==============================================================================
# EXPORTAR ARCHIVO TEMPORAL
# ==============================================================================
def exportar(df_ancho: pd.DataFrame, etiqueta="tmp") -> Tuple[pd.DataFrame, str]:
    ruta = os.path.join(tempfile.gettempdir(), f"estructuras_{etiqueta}_{int(time.time())}.xlsx")
    df_norm = _normalizar_columnas(df_ancho, COLUMNAS_BASE)
    df_largo = sanitizar(ancho_a_largo(df_norm))

    with pd.ExcelWriter(ruta, engine="openpyxl") as writer:
        df_largo.to_excel(writer, "estructuras", index=False)
        df_norm.to_excel(writer, "estructuras_ancha", index=False)

    return df_largo, ruta


# ==============================================================================
# CARGA DESDE EXCEL
# ==============================================================================
def cargar_excel() -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    archivo = st.file_uploader("📂 Archivo de estructuras (.xlsx)", type=["xlsx"], key="upl_estructuras")
    if not archivo: return None, None

    try:
        xls = pd.ExcelFile(archivo)
        hoja = next((s for s in xls.sheet_names if s.lower() == "estructuras"), xls.sheet_names[0])
        df_ancho = pd.read_excel(xls, sheet_name=hoja)
    except Exception as e:
        st.error(f"Error leyendo Excel: {e}")
        return None, None

    df_largo, ruta = exportar(df_ancho, etiqueta="excel")
    st.success(f"✅ {len(df_largo)} filas procesadas")
    return df_largo, ruta


# ==============================================================================
# CARGA DESDE TEXTO PEGADO
# ==============================================================================
def cargar_pegar() -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    txt = st.text_area("📋 Pega tu tabla (CSV/TSV)", height=200, key="txt_pegar_tabla").strip()
    if not txt:
        return None, None

    df = None
    for sep in ("\t", ",", ";", "|"):
        try:
            df = pd.read_csv(io.StringIO(txt), sep=sep)
            break
        except:
            pass
    if df is None:
        try:
            df = pd.read_csv(io.StringIO(txt), delim_whitespace=True)
        except:
            st.warning("No se detectaron filas.")
            return None, None

    df_largo, ruta = exportar(df, etiqueta="pega")
    st.success(f"✅ {len(df_largo)} filas procesadas")
    return df_largo, ruta


# ==============================================================================
# UI MINIMAL
# ==============================================================================
def ui() -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    if "df_puntos" not in st.session_state:
        st.session_state["df_puntos"] = pd.DataFrame(columns=COLUMNAS_BASE)

    df_wide = st.session_state["df_puntos"]

    st.subheader("✏️ Crear / Editar Punto")
    with st.form("frm_add", clear_on_submit=True):
        vals = {}
        vals["Punto"] = st.text_input("Punto")
        cols = st.columns(6)
        for i, key in enumerate(CAT_COLS):
            vals[key] = cols[i].text_input(key)
        if st.form_submit_button("➕ Añadir/Actualizar"):
            base = df_wide[df_wide["Punto"] != vals["Punto"]]
            st.session_state["df_puntos"] = pd.concat([base, pd.DataFrame([vals])], ignore_index=True)
            st.success("✅ Guardado")

    df_wide = st.session_state["df_puntos"]
    if not df_wide.empty:
        st.dataframe(df_wide, use_container_width=True)
        df_largo, ruta = exportar(df_wide, etiqueta="ui")
        return df_largo, ruta

    return None, None


# ==============================================================================
# FUNCIÓN PÚBLICA PARA app.py
# ==============================================================================
def seccion_entrada_estructuras(modo: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    modo = (modo or "").strip().lower()

    if modo == "excel":
        return cargar_excel()

    if modo == "pegar":
        return cargar_pegar()

    return ui()
