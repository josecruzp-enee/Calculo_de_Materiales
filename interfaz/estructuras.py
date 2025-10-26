# interfaz/estructuras.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import os
import re
import time
import tempfile
from typing import Tuple, List, Dict, Optional

import pandas as pd
import streamlit as st

# ------------------------------------------------------------
# 1) Definiciones base
# ------------------------------------------------------------
COLUMNAS_BASE: List[str] = [
    "Punto",
    "Poste",
    "Primario",
    "Secundario",
    "Retenidas",
    "Conexiones a tierra",
    "Transformadores",
]

CAT_COLS: List[str] = [
    "Poste",
    "Primario",
    "Secundario",
    "Retenidas",
    "Conexiones a tierra",
    "Transformadores",
]

# ------------------------------------------------------------
# 2) Utilidades de normalización/parsing
# ------------------------------------------------------------
def _normalizar_columnas(df: pd.DataFrame, columnas: List[str]) -> pd.DataFrame:
    df = df.copy()
    df = df.rename(columns={
        "Retenida": "Retenidas",
        "Aterrizaje": "Conexiones a tierra",
        "Transformador": "Transformadores",
    })
    for c in columnas:
        if c not in df.columns:
            df[c] = ""
    # Restringe al orden esperado
    return df[columnas]

def _norm_code_value(s) -> str:
    """Limpia código de estructura: trim + elimina sufijos '(...)' al final."""
    if pd.isna(s):
        return ""
    s = str(s).strip()
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s).strip()
    return s

def _split_cell_items(cell) -> List[str]:
    """Separa por comas/punto y coma/saltos de línea; ignora '-' y vacíos."""
    if not isinstance(cell, str):
        cell = "" if cell is None else str(cell)
    s = cell.strip().strip('"').strip("'")
    if not s or s == "-":
        return []
    parts = re.split(r"[,;\n\r]+", s)
    return [p.strip() for p in parts if p.strip()]

def _parse_item(piece: str) -> Tuple[str, int]:
    """
    Interpreta cantidad + código:
      '2× R-1' / '2x R-1' / '2 R-1' / '2B-I-4' / 'A-I-4 (E)'
    """
    m = re.match(r'^(\d+)\s*[x×]\s*(.+)$', piece, flags=re.I)
    if m:
        return _norm_code_value(m.group(2)), int(m.group(1))
    m = re.match(r'^(\d+)\s+(.+)$', piece)
    if m:
        return _norm_code_value(m.group(2)), int(m.group(1))
    m = re.match(r'^(\d+)([A-Za-z].+)$', piece)
    if m:
        return _norm_code_value(m.group(2)), int(m.group(1))
    return _norm_code_value(piece), 1

# ------------------------------------------------------------
# 3) Conversión ANCHO -> LARGO
# ------------------------------------------------------------
def expandir_ancho_a_largo(df_ancho: pd.DataFrame) -> pd.DataFrame:
    """
    Devuelve columnas: ['Punto','codigodeestructura','cantidad']
    """
    df = _normalizar_columnas(df_ancho, COLUMNAS_BASE).copy()
    rows: List[Dict[str, object]] = []

    for _, r in df.iterrows():
        punto = str(r.get("Punto", "")).strip()
        for col in CAT_COLS:
            piezas = _split_cell_items(str(r.get(col, "") or ""))
            for piece in piezas:
                code, qty = _parse_item(piece)
                if code:
                    rows.append({
                        "Punto": punto,
                        "codigodeestructura": code,
                        "cantidad": int(qty),
                    })

    out = pd.DataFrame(rows, columns=["Punto", "codigodeestructura", "cantidad"])
    return out

# ------------------------------------------------------------
# 4) Sanitización ESTRICTA para el DataFrame LARGO
# ------------------------------------------------------------
def _scalarize(x) -> str:
    """Convierte listas/tuplas/sets a cadena 'a, b, c'. Forza str para escalar."""
    if isinstance(x, (list, tuple, set)):
        return ", ".join(map(str, list(x)))
    if x is None:
        return ""
    return str(x)

def sanitizar_expandido(df_expandido: pd.DataFrame) -> pd.DataFrame:
    """
    Garantiza que:
      - 'Punto' y 'codigodeestructura' sean 1-D (str)
      - 'cantidad' sea int >=1
    Elimina filas vacías o inválidas.
    """
    df = df_expandido.copy()

    # Asegura columnas mínimas
    for col in ["Punto", "codigodeestructura", "cantidad"]:
        if col not in df.columns:
            df[col] = "" if col != "cantidad" else 0

    # Scalarizar y tipar
    df["Punto"] = df["Punto"].map(_scalarize).fillna("")
    df["codigodeestructura"] = df["codigodeestructura"].map(_scalarize).fillna("")
    # Normaliza código (quita sufijos '(E)/(P)/(...)')
    df["codigodeestructura"] = df["codigodeestructura"].map(_norm_code_value)

    # cantidad -> int (errores = 0)
    def _to_int_safe(v):
        try:
            return int(float(v))
        except Exception:
            return 0

    df["cantidad"] = df["cantidad"].map(_to_int_safe).fillna(0).astype(int)

    # Limpieza de filas inválidas
    df = df[(df["codigodeestructura"].str.len() > 0) & (df["cantidad"] > 0)].copy()

    # Trim final por si acaso
    df["Punto"] = df["Punto"].str.strip()
    df["codigodeestructura"] = df["codigodeestructura"].str.strip()

    # Índice limpio
    return df.reset_index(drop=True)

# ------------------------------------------------------------
# 5) Materialización a archivo temporal (opcional, útil para depurar)
# ------------------------------------------------------------
def _materializar_df_a_archivo(df_ancho: pd.DataFrame, etiqueta: str = "data") -> str:
    ts = int(time.time())
    ruta = os.path.join(tempfile.gettempdir(), f"estructuras_{etiqueta}_{ts}.xlsx")

    df_ancho_norm = _normalizar_columnas(df_ancho, COLUMNAS_BASE)
    df_largo = expandir_ancho_a_largo(df_ancho_norm)
    df_largo = sanitizar_expandido(df_largo)

    try:
        writer = pd.ExcelWriter(ruta, engine="openpyxl")
    except Exception:
        writer = pd.ExcelWriter(ruta, engine="xlsxwriter")

    with writer:
        df_largo.to_excel(writer, sheet_name="estructuras", index=False)
        df_ancho_norm.to_excel(writer, sheet_name="estructuras_ancha", index=False)

    # Debug liviano en Streamlit (no romper si falla)
    try:
        xls = pd.ExcelFile(ruta)
        hoja = next((s for s in xls.sheet_names if s.lower() == "estructuras"), xls.sheet_names[0])
        cols = list(pd.read_excel(xls, sheet_name=hoja, nrows=0).columns)
        st.caption("🔎 Estructuras generadas (debug)")
        st.write({"ruta": ruta, "hojas": xls.sheet_names, "columnas_estructuras": cols})
    except Exception:
        pass

    return ruta

# ------------------------------------------------------------
# 6) Carga de datos (Excel o texto pegado)
# ------------------------------------------------------------
def _parsear_texto_a_df(texto: str, columnas: List[str]) -> pd.DataFrame:
    txt = (texto or "").strip()
    if not txt:
        return pd.DataFrame(columns=columnas)

    # Intenta con separadores comunes
    for sep in ("\t", ",", ";", "|"):
        try:
            df = pd.read_csv(io.StringIO(txt), sep=sep)
            return _normalizar_columnas(df, columnas)
        except Exception:
            pass

    # Fallback: espacios en blanco
    try:
        df = pd.read_csv(io.StringIO(txt), delim_whitespace=True)
        return _normalizar_columnas(df, columnas)
    except Exception:
        return pd.DataFrame(columns=columnas)

def cargar_desde_excel() -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    archivo = st.file_uploader("Archivo de estructuras (.xlsx)", type=["xlsx"], key="upl_estructuras")
    if not archivo:
        return None, None
    try:
        xls = pd.ExcelFile(archivo)
        hoja = next((s for s in xls.sheet_names if s.strip().lower() == "estructuras"), xls.sheet_names[0])
        df_ancho = pd.read_excel(xls, sheet_name=hoja)
    except Exception as e:
        st.error(f"Error leyendo el Excel: {e}")
        return None, None

    df_ancho = _normalizar_columnas(df_ancho, COLUMNAS_BASE)
    ruta_tmp = _materializar_df_a_archivo(df_ancho, "excel")
    df_largo = expandir_ancho_a_largo(df_ancho)
    df_largo = sanitizar_expandido(df_largo)
    st.success(f"✅ Cargadas {len(df_largo)} filas (largo) desde Excel")
    return df_largo, ruta_tmp

def pegar_tabla() -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    texto = st.text_area("Pega aquí tu tabla (CSV/TSV). Soporta coma y saltos de línea en celdas.",
                         height=200, key="txt_pegar_tabla")
    if not texto:
        return None, None
    df_ancho = _parsear_texto_a_df(texto, COLUMNAS_BASE)
    if df_ancho is None or df_ancho.empty:
        st.warning("No se detectaron filas válidas en el texto.")
        return None, None
    ruta_tmp = _materializar_df_a_archivo(df_ancho, "pega")
    df_largo = expandir_ancho_a_largo(df_ancho)
    df_largo = sanitizar_expandido(df_largo)
    st.success(f"✅ Tabla pegada convertida ({len(df_largo)} filas)")
    return df_largo, ruta_tmp

# ------------------------------------------------------------
# 7) UI mínima con desplegables (opcional y compacta)
#    - Mantiene estado por punto y devuelve largo saneado
# ------------------------------------------------------------
def _ensure_sesion():
    if "df_puntos" not in st.session_state:
        st.session_state["df_puntos"] = pd.DataFrame(columns=COLUMNAS_BASE)

def _consolidado_a_fila(punto: str, buckets: Dict[str, Dict[str, int]]) -> Dict[str, str]:
    def _render(cat: str) -> str:
        data = buckets.get(cat, {})
        if not data:
            return ""
        parts = [f"{n}× {c}" if n > 1 else c for c, n in data.items()]
        return ", ".join(parts)
    return {
        "Punto": punto,
        "Poste": _render("Poste"),
        "Primario": _render("Primario"),
        "Secundario": _render("Secundario"),
        "Retenidas": _render("Retenidas"),
        "Conexiones a tierra": _render("Conexiones a tierra"),
        "Transformadores": _render("Transformadores"),
    }

def listas_desplegables() -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    _ensure_sesion()
    st.subheader("🏗️ Estructuras del Proyecto (UI simple)")
    df_wide = st.session_state["df_puntos"]

    # Entrada rápida manual
    st.markdown("**Agregar/editar una fila (ancho)**")
    with st.form(key="frm_add_row", clear_on_submit=False):
        punto = st.text_input("Punto", value=f"Punto {len(df_wide)+1 if df_wide is not None else 1}")
        cols = st.columns(6)
        poste = cols[0].text_input("Poste", value="")
        pri = cols[1].text_input("Primario", value="")
        sec = cols[2].text_input("Secundario", value="")
        ret = cols[3].text_input("Retenidas", value="")
        ct  = cols[4].text_input("Conexiones a tierra", value="")
        tr  = cols[5].text_input("Transformadores", value="")
        submitted = st.form_submit_button("➕ Añadir/Actualizar punto")
        if submitted:
            fila = {
                "Punto": punto, "Poste": poste, "Primario": pri, "Secundario": sec,
                "Retenidas": ret, "Conexiones a tierra": ct, "Transformadores": tr
            }
            base = df_wide if df_wide is not None and not df_wide.empty else pd.DataFrame(columns=COLUMNAS_BASE)
            base = base[base["Punto"] != punto]
            st.session_state["df_puntos"] = pd.concat([base, pd.DataFrame([fila])], ignore_index=True)
            df_wide = st.session_state["df_puntos"]
            st.success("✅ Punto guardado/actualizado")

    if df_wide is not None and not df_wide.empty:
        st.dataframe(df_wide.sort_values(by="Punto"), use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Descargar CSV (ancho)",
            df_wide.sort_values(by="Punto").to_csv(index=False).encode("utf-8"),
            file_name="estructuras_puntos.csv",
            mime="text/csv",
            use_container_width=True,
        )
        ruta_tmp = _materializar_df_a_archivo(df_wide, "ui")
        df_largo = expandir_ancho_a_largo(df_wide)
        df_largo = sanitizar_expandido(df_largo)
        return df_largo, ruta_tmp

    return None, None

# ------------------------------------------------------------
# 8) Función pública para app.py
# ------------------------------------------------------------
def seccion_entrada_estructuras(modo_carga: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Devuelve (df_estructuras_largo, ruta_estructuras_xlsx) según el modo:
      - "excel"  -> cargar desde .xlsx
      - "pegar"  -> pegar CSV/TSV en texto
      - otro     -> UI simple de puntos
    SIEMPRE retorna df_largo ya SANITIZADO para evitar errores de groupby.
    """
    modo = (modo_carga or "").strip().lower()
    if modo == "excel":
        return cargar_desde_excel()
    if modo == "pegar":
        return pegar_tabla()

    df, ruta = listas_desplegables()
    if df is None:
        return None, ruta

    # Debug visible y retorno final
    st.markdown("### 🧪 DEBUG: vista previa (ya sanitizado)")
    st.dataframe(df.head(10), use_container_width=True)
    st.write("**Columnas:**", list(df.columns))
    st.write("**dtypes:**", df.dtypes.to_dict())
    st.write("**Shape:**", df.shape)

    return df, ruta
