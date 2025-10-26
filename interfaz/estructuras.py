# interfaz/estructuras.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import io
from typing import Optional, Tuple, List, Dict

import pandas as pd
import streamlit as st

# =============================================================================
# Configuración base y utilidades seguras
# =============================================================================

COLUMNAS_BASE: List[str] = [
    "Punto",
    "Poste",
    "Primario",
    "Secundario",
    "Retenidas",
    "Conexiones a tierra",
    "Transformadores",
]

def _normalizar_columnas(df: pd.DataFrame, columnas: List[str]) -> pd.DataFrame:
    df = df.copy()
    for c in columnas:
        if c not in df.columns:
            df[c] = ""
    return df[columnas]

def _parsear_texto_a_df(texto: str, columnas: List[str]) -> pd.DataFrame:
    txt = (texto or "").strip()
    if not txt:
        return pd.DataFrame(columns=columnas)
    df = None
    for sep in ("\t", ",", ";", "|"):
        try:
            df = pd.read_csv(io.StringIO(txt), sep=sep)
            break
        except Exception:
            df = None
    if df is None:
        try:
            df = pd.read_csv(io.StringIO(txt), delim_whitespace=True)
        except Exception:
            return pd.DataFrame(columns=columnas)
    return _normalizar_columnas(df, columnas)

# =============================================================================
# Modo: Excel
# =============================================================================

def cargar_desde_excel() -> Tuple[pd.DataFrame | None, str | None]:
    archivo = st.file_uploader("Archivo de estructuras (.xlsx)", type=["xlsx"], key="upl_estructuras")
    if not archivo:
        return None, None
    nombre = getattr(archivo, "name", "estructura_lista.xlsx")
    try:
        df = pd.read_excel(archivo)
    except Exception as e:
        st.error(f"Error leyendo el Excel: {e}")
        return None, nombre
    df = _normalizar_columnas(df, COLUMNAS_BASE)
    st.success(f"✅ Cargadas {len(df)} filas desde {nombre}")
    return df, nombre

# =============================================================================
# Modo: Pegar tabla (CSV/TSV)
# =============================================================================

def pegar_tabla() -> Tuple[pd.DataFrame | None, str | None]:
    texto_pegado = st.text_area("Pega aquí tu tabla (CSV/TSV)", height=200, key="txt_pegar_tabla")
    if not texto_pegado:
        return None, None
    df = _parsear_texto_a_df(texto_pegado, COLUMNAS_BASE)
    st.success(f"✅ Tabla cargada con {len(df)} filas")
    return df, "PEGA/TEXTO"

# =============================================================================
# Modo: Desplegables (Listas PRO) con cantidad + agregar
# =============================================================================

def _cargar_opciones_catalogo() -> Dict[str, Dict[str, object]]:
    """
    Intenta cargar opciones desde modulo.desplegables.cargar_opciones().
    Estructura esperada por categoría:
      {"valores": [cod1, cod2, ...], "etiquetas": {cod1: "cod1 – desc", ...}}
    Si no existe el módulo, retorna un fallback mínimo.
    """
    try:
        from modulo.desplegables import cargar_opciones  # type: ignore
        opciones = cargar_opciones()
        # Normalización suave
        for key in ["Poste", "Primaria", "Secundaria", "Retenidas", "Conexiones a tierra", "Transformadores"]:
            opciones.setdefault(key, {"valores": [], "etiquetas": {}})
            opciones[key].setdefault("valores", [])
            opciones[key].setdefault("etiquetas", {})
        return opciones
    except Exception:
        # Fallback simple
        return {
            "Poste": {"valores": ["Madera", "Cemento"], "etiquetas": {}},
            "Primaria": {"valores": ["1/0 ACSR", "3/0 ACSR", "4/0 ACSR"], "etiquetas": {}},
            "Secundaria": {"valores": ["#2 ACSR", "1/0 ACSR"], "etiquetas": {}},
            "Retenidas": {"valores": ["R-0", "R-1", "R-2"], "etiquetas": {}},
            "Conexiones a tierra": {"valores": ['Sin conexión', 'Varilla 5/8" x 8\'', "Malla"], "etiquetas": {}},
            "Transformadores": {"valores": ["Ninguno", "25 kVA", "37.5 kVA", "50 kVA"], "etiquetas": {}},
        }

def _ensure_df_sesion():
    if "df_puntos" not in st.session_state:
        st.session_state["df_puntos"] = pd.DataFrame(columns=COLUMNAS_BASE)

def _ensure_punto_en_edicion():
    if "punto_en_edicion" not in st.session_state:
        df = st.session_state.get("df_puntos", pd.DataFrame())
        if isinstance(df, pd.DataFrame) and not df.empty:
            st.session_state["punto_en_edicion"] = df["Punto"].iloc[0]
        else:
            st.session_state["punto_en_edicion"] = "Punto 1"

def _ensure_data_consolidada():
    if "puntos_data" not in st.session_state:
        st.session_state["puntos_data"] = {}
    p = st.session_state["punto_en_edicion"]
    if p not in st.session_state["puntos_data"]:
        st.session_state["puntos_data"][p] = {
            "Poste": {},
            "Primario": {},
            "Secundario": {},
            "Retenidas": {},
            "Conexiones a tierra": {},
            "Transformadores": {},
        }

def _add_item(cat: str, code: str, qty: int):
    if not code or qty <= 0:
        return
    p = st.session_state["punto_en_edicion"]
    bucket = st.session_state["puntos_data"][p][cat]
    bucket[code] = bucket.get(code, 0) + int(qty)

def _remove_item(cat: str, code: str, all_qty: bool = False):
    p = st.session_state["punto_en_edicion"]
    bucket = st.session_state["puntos_data"][p][cat]
    if code in bucket:
        if all_qty or bucket[code] <= 1:
            bucket.pop(code, None)
        else:
            bucket[code] -= 1

def _render_cat_str(punto: str, categoria: str) -> str:
    data = st.session_state["puntos_data"][punto][categoria]
    if not data:
        return ""
    parts = []
    for code, n in data.items():
        parts.append(f"{n}× {code}" if n > 1 else code)
    return ", ".join(parts)

def _fila_categoria_ui(label: str, valores: list[str], etiquetas: dict, key_prefix: str):
    st.markdown(f"**{label}**")
    c1, c2, c3 = st.columns([7, 1.1, 1.9])
    with c1:
        sel = st.selectbox(
            "", valores, index=0 if valores else None,
            key=f"{key_prefix}_{label}_sel",
            label_visibility="collapsed",
            format_func=lambda x: etiquetas.get(x, x),
        )
    with c2:
        qty = st.number_input(
            " ", min_value=1, max_value=99, step=1, value=1,
            key=f"{key_prefix}_{label}_qty", label_visibility="collapsed"
        )
    with c3:
        if st.button("➕ Agregar", key=f"{key_prefix}_{label}_add"):
            _add_item(label, sel, qty)
            st.success(f"Añadido: {qty}× {etiquetas.get(sel, sel)}")

def _consolidado_a_fila(punto: str) -> Dict[str, str]:
    return {
        "Punto": punto,
        "Poste": _render_cat_str(punto, "Poste"),
        "Primario": _render_cat_str(punto, "Primario"),
        "Secundario": _render_cat_str(punto, "Secundario"),
        "Retenidas": _render_cat_str(punto, "Retenidas"),
        "Conexiones a tierra": _render_cat_str(punto, "Conexiones a tierra"),
        "Transformadores": _render_cat_str(punto, "Transformadores"),
    }

def _pick_vals_labels(opciones: dict, prefer: list[str], fuzzy_fragments: list[str] = None):
    """
    Devuelve (valores, etiquetas) probando primero claves 'prefer' y luego
    una búsqueda suave por fragmentos (fuzzy).
    """
    # 1) intenta claves preferidas en orden
    for k in prefer:
        blk = opciones.get(k)
        if blk and blk.get("valores"):
            vals = blk.get("valores", [])
            labs = blk.get("etiquetas", {}) or {}
            # asegúrate de tener etiquetas básicas
            if not labs:
                labs = {c: c for c in vals}
            return vals, labs

    # 2) búsqueda fuzzy por fragmentos
    if fuzzy_fragments:
        for k, blk in opciones.items():
            k_low = str(k).lower()
            if any(f in k_low for f in fuzzy_fragments):
                if blk and blk.get("valores"):
                    vals = blk.get("valores", [])
                    labs = blk.get("etiquetas", {}) or {}
                    if not labs:
                        labs = {c: c for c in vals}
                    return vals, labs

    # 3) vacío
    return [], {}

# ---------- Opciones por categoría (robusto a MT/BT y otras variantes) ----------
vals_poste, lab_poste = _pick_vals_labels(
    opciones,
    prefer=["Poste"],
    fuzzy_fragments=["poste"]
)

# PRIMARIO: soporta Primario/Primaria/MT/Media Tensión, etc.
vals_pri, lab_pri = _pick_vals_labels(
    opciones,
    prefer=["Primario", "Primaria", "MT", "Media Tensión", "Media Tension", "MT Primario", "Primaria MT"],
    fuzzy_fragments=["primar", "media", "mt"]
)

# SECUNDARIO: soporta Secundario/Secundaria/BT/Baja Tensión, etc.
vals_sec, lab_sec = _pick_vals_labels(
    opciones,
    prefer=["Secundario", "Secundaria", "BT", "Baja Tensión", "Baja Tension", "BT Secundario", "Secundaria BT"],
    fuzzy_fragments=["secund", "baja", "bt"]
)

vals_ret, lab_ret = _pick_vals_labels(
    opciones,
    prefer=["Retenidas"],
    fuzzy_fragments=["reten"]
)

vals_ct, lab_ct = _pick_vals_labels(
    opciones,
    prefer=["Conexiones a tierra", "Tierra", "Puesta a tierra"],
    fuzzy_fragments=["tierra", "puesta"]
)

vals_tr, lab_tr = _pick_vals_labels(
    opciones,
    prefer=["Transformadores", "Transformador"],
    fuzzy_fragments=["trafo", "transfor"]
)

# (Opcional) ver las claves reales que trae tu catálogo
# st.caption(f"Claves en catálogo: {list(opciones.keys())}")


# =============================================================================
# Función pública llamada por app.py
# =============================================================================

def seccion_entrada_estructuras(modo_carga: str) -> Tuple[pd.DataFrame | None, str | None]:
    """
    Devuelve siempre una tupla (df_estructuras, ruta_estructuras) según el modo:
      - "Excel"  -> carga desde file_uploader
      - "Pegar"  -> parsea texto CSV/TSV
      - otro     -> UI de Desplegables (Listas PRO)
    """
    modo = (modo_carga or "").strip().lower()

    if modo == "excel":
        return cargar_desde_excel()

    if modo == "pegar":
        return pegar_tabla()

    # Cualquier otro valor cae a los desplegables
    return listas_desplegables()
