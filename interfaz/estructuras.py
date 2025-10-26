# interfaz/estructuras.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import os
import re
import time
import tempfile
from typing import Tuple, Optional, List, Dict

import numpy as np
import pandas as pd
import streamlit as st

# ==============================================================================
# Config base
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
CAT_COLS: List[str] = COLUMNAS_BASE[1:]  # todas menos Punto

# ==============================================================================
# Utilidades de normalización / parseo
# ==============================================================================
def _normalizar_columnas(df: pd.DataFrame, columnas: List[str]) -> pd.DataFrame:
    """Asegura columnas esperadas y renombra variantes comunes."""
    if df is None or not isinstance(df, pd.DataFrame):
        return pd.DataFrame(columns=columnas)

    df = df.copy()
    df = df.rename(columns={
        "Retenida": "Retenidas",
        "Aterrizaje": "Conexiones a tierra",
        "Transformador": "Transformadores",
    })
    for c in columnas:
        if c not in df.columns:
            df[c] = ""
    # Reordenar y devolver solo columnas esperadas
    return df[columnas]

def _limpiar_codigo(s: str) -> str:
    """Quita sufijos finales tipo '(E)', '(P)', '(R)' y espacios."""
    if pd.isna(s):
        return ""
    s = str(s).strip()
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s)
    return s.strip()

def _split_cell(cell) -> List[str]:
    """Divide por coma/; y saltos de línea; ignora '-' y vacíos."""
    if not isinstance(cell, str):
        cell = str(cell or "")
    cell = cell.strip()
    if cell in ("", "-"):
        return []
    return [p.strip() for p in re.split(r"[,;\n\r]+", cell) if p.strip()]

def _parse_item(piece: str) -> Tuple[str, int]:
    """
    Interpreta cantidad + código:
      '2× R-1' / '2x R-1' / '2 R-1' / '2B-I-4' / 'A-I-4 (E)'
    """
    m = re.match(r'^(\d+)\s*[x×]\s*(.+)$', piece, flags=re.I)
    if m:
        return _limpiar_codigo(m.group(2)), int(m.group(1))
    m = re.match(r'^(\d+)\s+(.+)$', piece)
    if m:
        return _limpiar_codigo(m.group(2)), int(m.group(1))
    m = re.match(r'^(\d+)([A-Za-z].+)$', piece)
    if m:
        return _limpiar_codigo(m.group(2)), int(m.group(1))
    return _limpiar_codigo(piece), 1

# ==============================================================================
# Conversión ANCHO → LARGO (sin saneo)
# ==============================================================================
def _expandir_ancho_a_largo(df_ancho: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte la tabla ANCHA a LARGA con columnas:
    ['Punto', 'codigodeestructura', 'cantidad'] (tipos crudos).
    """
    df = _normalizar_columnas(df_ancho, COLUMNAS_BASE)
    filas: List[Dict[str, object]] = []
    for _, r in df.iterrows():
        punto = str(r.get("Punto", "")).strip()
        for col in CAT_COLS:
            piezas = _split_cell(r.get(col, ""))
            for p in piezas:
                code, qty = _parse_item(p)
                if code:
                    filas.append({
                        "Punto": punto,
                        "codigodeestructura": code,
                        "cantidad": int(qty),
                    })
    return pd.DataFrame(filas, columns=["Punto", "codigodeestructura", "cantidad"])

# ==============================================================================
# Saneado 1-D (lo que asegura que exportacion.py nunca falle)
# ==============================================================================
def _scalarize(x) -> str:
    if isinstance(x, (list, tuple, set)):
        return ", ".join(map(str, x))
    if isinstance(x, np.ndarray):
        return ", ".join(map(str, x.tolist()))
    if x is None:
        return ""
    return str(x)

def _to_int_safe(v) -> int:
    try:
        iv = int(float(v))
        return iv if iv >= 0 else 0
    except Exception:
        return 0

def sanitizar_expandido(df_expandido: pd.DataFrame) -> pd.DataFrame:
    """
    Devuelve SIEMPRE un DataFrame 1-D con columnas:
    ['Punto','codigodeestructura','cantidad'] listo para groupby.
    """
    if df_expandido is None or not isinstance(df_expandido, pd.DataFrame) or df_expandido.empty:
        return pd.DataFrame(columns=["Punto", "codigodeestructura", "cantidad"])

    df = df_expandido.copy()

    # Aplana nombres por si vienen como tuplas/MultiIndex
    df.columns = [(" / ".join(map(str, c)) if isinstance(c, tuple) else str(c)) for c in df.columns]

    # Asegura columnas mínimas
    for col in ["Punto", "codigodeestructura", "cantidad"]:
        if col not in df.columns:
            df[col] = "" if col != "cantidad" else 0

    # Scalariza y limpia texto
    df["Punto"] = df["Punto"].map(_scalarize).fillna("").astype(str).str.strip()
    df["codigodeestructura"] = df["codigodeestructura"].map(_scalarize).fillna("").astype(str).str.strip()
    df["codigodeestructura"] = df["codigodeestructura"].map(_limpiar_codigo)

    # cantidad → int seguro
    df["cantidad"] = df["cantidad"].map(_to_int_safe).astype(int)

    # Filtra inválidos y devuelve solo lo necesario
    df = df[(df["codigodeestructura"] != "") & (df["cantidad"] > 0)]
    return df.loc[:, ["Punto", "codigodeestructura", "cantidad"]].reset_index(drop=True)

# ==============================================================================
# Materialización a archivo temporal (xlsx con 2 hojas)
# ==============================================================================
def _materializar_df_a_archivo(df_ancho: pd.DataFrame, etiqueta: str = "data") -> str:
    """
    Crea un .xlsx temporal con:
      • Hoja 'estructuras'        -> LARGO saneado
      • Hoja 'estructuras_ancha'  -> ANCHO normalizado
    Devuelve la ruta absoluta.
    """
    ts = int(time.time())
    ruta = os.path.join(tempfile.gettempdir(), f"estructuras_{etiqueta}_{ts}.xlsx")

    df_ancho_norm = _normalizar_columnas(df_ancho, COLUMNAS_BASE)
    df_largo = sanitizar_expandido(_expandir_ancho_a_largo(df_ancho_norm))

    try:
        writer = pd.ExcelWriter(ruta, engine="openpyxl")
    except Exception:
        writer = pd.ExcelWriter(ruta, engine="xlsxwriter")

    with writer:
        df_largo.to_excel(writer, sheet_name="estructuras", index=False)
        df_ancho_norm.to_excel(writer, sheet_name="estructuras_ancha", index=False)

    return ruta

# ==============================================================================
# Carga desde Excel
# ==============================================================================
def cargar_desde_excel() -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    archivo = st.file_uploader("📂 Archivo de estructuras (.xlsx)", type=["xlsx"], key="upl_estructuras")
    if not archivo:
        return None, None
    try:
        xls = pd.ExcelFile(archivo)
        hoja = next((s for s in xls.sheet_names if s.strip().lower() == "estructuras"), xls.sheet_names[0])
        df_ancho = pd.read_excel(xls, sheet_name=hoja)
    except Exception as e:
        st.error(f"Error leyendo el Excel: {e}")
        return None, None

    df_largo = sanitizar_expandido(_expandir_ancho_a_largo(df_ancho))
    ruta_tmp = _materializar_df_a_archivo(df_ancho, "excel")
    st.success(f"✅ Cargadas {len(df_largo)} filas (largo) desde Excel")
    return df_largo, ruta_tmp

# ==============================================================================
# Carga desde texto pegado (CSV/TSV)
# ==============================================================================
def _parsear_texto_a_df(texto: str, columnas: List[str]) -> pd.DataFrame:
    txt = (texto or "").strip()
    if not txt:
        return pd.DataFrame(columns=columnas)

    # intenta separadores comunes
    for sep in ("\t", ",", ";", "|"):
        try:
            df = pd.read_csv(io.StringIO(txt), sep=sep)
            return _normalizar_columnas(df, columnas)
        except Exception:
            pass

    # fallback: por espacios
    try:
        df = pd.read_csv(io.StringIO(txt), delim_whitespace=True)
        return _normalizar_columnas(df, columnas)
    except Exception:
        return pd.DataFrame(columns=columnas)

def pegar_tabla() -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    texto_pegado = st.text_area("📋 Pega tu tabla (CSV/TSV). Soporta comas y saltos de línea en celdas.",
                                height=200, key="txt_pegar_tabla")
    if not texto_pegado:
        return None, None
    df_ancho = _parsear_texto_a_df(texto_pegado, COLUMNAS_BASE)
    if df_ancho is None or df_ancho.empty:
        st.warning("No se detectaron filas válidas en el texto.")
        return None, None

    df_largo = sanitizar_expandido(_expandir_ancho_a_largo(df_ancho))
    ruta_tmp = _materializar_df_a_archivo(df_ancho, "pega")
    st.success(f"✅ Tabla pegada convertida ({len(df_largo)} filas)")
    return df_largo, ruta_tmp

# ==============================================================================
# UI mínima (desplegables/inputs simples)
# ==============================================================================
def _ensure_df_sesion():
    if "df_puntos" not in st.session_state:
        st.session_state["df_puntos"] = pd.DataFrame(columns=COLUMNAS_BASE)

def ui_desplegables() -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    UI simple para ingresar filas ANCHAS y producir salida LARGA saneada.
    """
    _ensure_df_sesion()
    df_wide = st.session_state["df_puntos"]

    st.subheader("🏗️ Estructuras del Proyecto (UI)")
    with st.form("frm_add", clear_on_submit=True):
        punto = st.text_input("Punto", value=f"Punto {len(df_wide)+1 if not df_wide.empty else 1}")
        cols = st.columns(6)
        poste = cols[0].text_input("Poste")
        prim  = cols[1].text_input("Primario")
        sec   = cols[2].text_input("Secundario")
        ret   = cols[3].text_input("Retenidas")
        ct    = cols[4].text_input("Conexiones a tierra")
        trafo = cols[5].text_input("Transformadores")
        if st.form_submit_button("➕ Añadir/Actualizar"):
            fila = {
                "Punto": punto,
                "Poste": poste,
                "Primario": prim,
                "Secundario": sec,
                "Retenidas": ret,
                "Conexiones a tierra": ct,
                "Transformadores": trafo,
            }
            base = df_wide[df_wide["Punto"] != punto] if not df_wide.empty else pd.DataFrame(columns=COLUMNAS_BASE)
            st.session_state["df_puntos"] = pd.concat([base, pd.DataFrame([fila])], ignore_index=True)
            st.success("✅ Punto guardado/actualizado")

    df_wide = st.session_state["df_puntos"]
    if not df_wide.empty:
        st.markdown("#### 🗂️ Puntos (ANCHO)")
        st.dataframe(df_wide.sort_values("Punto"), use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Descargar CSV (ancho)",
            df_wide.sort_values("Punto").to_csv(index=False).encode("utf-8"),
            file_name="estructuras_puntos.csv",
            mime="text/csv",
            use_container_width=True,
        )
        # Materializamos archivo (dos hojas) y producimos salida larga saneada
        ruta_tmp = _materializar_df_a_archivo(df_wide, "ui")
        df_largo = sanitizar_expandido(_expandir_ancho_a_largo(df_wide))
        return df_largo, ruta_tmp

    return None, None

# ==============================================================================
# Función pública: llamada por app.py
# ==============================================================================
def seccion_entrada_estructuras(modo_carga: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Devuelve (df_estructuras_largo, ruta_estructuras_xlsx) según el modo:
      - "excel"  -> cargar desde .xlsx
      - "pegar"  -> pegar CSV/TSV en texto
      - otro     -> UI con inputs simples
    La salida SIEMPRE está saneada (1-D) para evitar errores en exportación.py.
    """
    modo = (modo_carga or "").strip().lower()
    if modo == "excel":
        return cargar_desde_excel()
    if modo == "pegar":
        return pegar_tabla()
    return ui_desplegables()
