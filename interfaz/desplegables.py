# modulo/desplegables.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
from collections import Counter
from typing import Dict, Any

import pandas as pd
import streamlit as st

# =============================================================================
# RUTA DEL CATÁLOGO
# =============================================================================
REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
RUTA_EXCEL = os.path.join(REPO_ROOT, "data", "Estructura_datos.xlsx")


# =============================================================================
# DEBUG (NO ejecutar en import)
# =============================================================================
def debug_catalogo_excel(ruta_excel: str = RUTA_EXCEL):
    """
    Debug visual del catálogo para Streamlit.
    OJO: llamala desde tu UI (no en toplevel), por ejemplo:
        with st.expander("🧪 Debug catálogo"):
            debug_catalogo_excel()
    """
    st.subheader("🧪 DEBUG CATÁLOGO")
    st.write("RUTA:", ruta_excel)
    st.write("EXISTE:", os.path.exists(ruta_excel))
    st.write("CWD:", os.getcwd())

    # listar ./data si existe (útil en Cloud)
    try:
        st.write("Contenido ./data:", os.listdir("data") if os.path.isdir("data") else "NO existe ./data")
    except Exception as e:
        st.write("No pude listar ./data:", e)

    if not os.path.exists(ruta_excel):
        st.error("❌ NO existe el Excel en esa ruta. En Cloud esto es lo #1.")
        return None

    try:
        xls = pd.ExcelFile(ruta_excel)
        st.write("HOJAS:", xls.sheet_names)
    except Exception as e:
        st.error(f"❌ No pude abrir el Excel: {e}")
        return None

    hoja = next((s for s in xls.sheet_names if s.strip().lower() in ("indice", "índice")), None)
    st.write("HOJA indice detectada:", hoja)

    if not hoja:
        st.error("❌ No encuentro hoja indice/índice.")
        return None

    df = pd.read_excel(xls, sheet_name=hoja)
    df.columns = df.columns.astype(str).str.replace("\xa0", " ").str.strip()
    st.write("COLUMNAS:", list(df.columns))
    st.dataframe(df.head(15))
    return df


# =============================================================================
# CARGA DE OPCIONES DESDE "indice"
# =============================================================================
def _normalizar_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.astype(str).str.replace("\xa0", " ").str.strip()
    return df


def _resolver_columnas(df: pd.DataFrame):
    """
    Encuentra columnas de: Clasificación, Código, Descripción
    soportando variaciones del Excel (tildes, espacios, nombres largos).
    """
    def norm(s: str) -> str:
        return str(s).strip().lower()

    cols = {norm(c): c for c in df.columns}  # mapa normalizado -> original

    # 1) Clasificación
    clas_col = None
    for k in cols:
        if "clasific" in k:
            clas_col = cols[k]
            break

    # 2) Código
    cod_col = None
    for k in cols:
        if "codigo de estructura" in k or ("codigo" in k and "estructura" in k):
            cod_col = cols[k]
            break
    if not cod_col:
        for k in cols:
            if "codigo" in k:
                cod_col = cols[k]
                break

    # 3) Descripción
    desc_col = None
    for k in cols:
        if "descrip" in k:
            desc_col = cols[k]
            break

    return clas_col, cod_col, desc_col



import streamlit as st

def cargar_opciones(ruta_excel: str = RUTA_EXCEL) -> Dict[str, Dict[str, Any]]:
    if not os.path.exists(ruta_excel):
        st.error(f"CATÁLOGO: NO existe el archivo -> {ruta_excel}")
        return {}

    xls = pd.ExcelFile(ruta_excel)
    st.write("CATÁLOGO: hojas detectadas:", xls.sheet_names)

    hoja = next((s for s in xls.sheet_names if s.strip().lower() in ("indice", "índice")), None)
    if not hoja:
        st.error("CATÁLOGO: No encontré hoja llamada 'indice' o 'índice'")
        return {}

    df = pd.read_excel(xls, sheet_name=hoja)
    df = _normalizar_cols(df)

    clas_col, cod_col, desc_col = _resolver_columnas(df)
    st.write("CATÁLOGO: columnas resueltas:", {"clas": clas_col, "cod": cod_col, "desc": desc_col})

    if not clas_col or not cod_col:
        st.error("CATÁLOGO: No pude resolver columnas (clasificación/código). Revisar nombres de columnas en la hoja índice.")
        return {}

    # normalizar valores
    df[clas_col] = df[clas_col].astype(str).str.replace("\xa0", " ").str.strip()
    df[cod_col] = df[cod_col].astype(str).str.replace("\xa0", " ").str.strip()
    if desc_col and desc_col in df.columns:
        df[desc_col] = df[desc_col].astype(str).str.replace("\xa0", " ").str.strip()

    opciones = {}
    for clasificacion in df[clas_col].dropna().astype(str).unique():
        clasificacion = str(clasificacion).replace("\xa0", " ").strip()
        if not clasificacion:
            continue

        subset = df[df[clas_col] == clasificacion]

        codigos = subset[cod_col].dropna().astype(str).str.strip().tolist()

        etiquetas = {}
        if desc_col and desc_col in subset.columns:
            for _, row in subset.iterrows():
                if pd.notna(row.get(cod_col)):
                    cod = str(row[cod_col]).strip()
                    desc = str(row.get(desc_col, "")).strip() if pd.notna(row.get(desc_col)) else ""
                    etiquetas[cod] = f"{cod} – {desc}".strip()
        else:
            etiquetas = {str(c).strip(): str(c).strip() for c in codigos}

        opciones[clasificacion] = {"valores": codigos, "etiquetas": etiquetas}

    # Normaliza nombres de categoría para calzar con tu UI
    mapping = {
        "Poste": "Poste",
        "Primaria": "Primario",
        "Primario": "Primario",
        "Secundaria": "Secundario",
        "Secundario": "Secundario",
        "Retenidas": "Retenidas",
        "Conexiones a tierra": "Conexiones a tierra",
        "Conexiones a tierra / Protección": "Conexiones a tierra",
        "Protección": "Protección",
        "Proteccion": "Protección",
        "Transformadores": "Transformadores",
        "Luminarias": "Luminarias",
        "Luminaria": "Luminarias",
    }

    normalizado = {}
    for k, v in opciones.items():
        kk = mapping.get(str(k).replace("\xa0", " ").strip(), str(k).replace("\xa0", " ").strip())
        normalizado[kk] = v

    return normalizado


# =============================================================================
# Helpers de parseo (2x R-1  <->  Counter)
# =============================================================================
def _parse_str_to_counter(s: str) -> Counter:
    if not s:
        return Counter()
    s = s.replace("+", ",")
    parts = [p.strip() for p in s.split(",") if p.strip()]
    c = Counter()
    for p in parts:
        low = p.lower()
        if "x" in low:
            try:
                n, cod = low.split("x", 1)
                n = int(n.strip())
                cod = cod.strip().upper()
                if cod:
                    c[cod] += max(1, n)
                continue
            except Exception:
                pass
        c[p.upper()] += 1
    return c


def _counter_to_str(c: Counter) -> str:
    if not c:
        return ""
    partes = []
    for cod, n in c.items():
        partes.append(f"{n}x {cod}" if n > 1 else cod)
    return " , ".join(partes)


# =============================================================================
# UI: picker con cantidad
# =============================================================================
def _scoped_css_once():
    if st.session_state.get("_xpicker_css", False):
        return
    st.session_state["_xpicker_css"] = True
    st.markdown(
        """
        <style>
        .xpicker .count-pill{
            display:inline-block; min-width:28px; padding:2px 8px;
            border-radius:999px; text-align:center; font-weight:600;
            background:#f1f1f1; border:1px solid #e6e6e6;
        }
        .xpicker .row{
            padding:6px 8px; border:1px solid #eee; border-radius:10px;
            margin-bottom:6px; background:rgba(0,0,0,0.01);
        }
        .xpicker .stButton>button{
            padding:4px 10px; border-radius:10px;
        }
        .xpicker .muted{ color:#666; font-size:12px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _short(label: str, maxlen: int = 52) -> str:
    return label if len(label) <= maxlen else label[:maxlen - 1] + "…"


def _render_lista(contador: Counter, datos: dict, state_key: str):
    if not contador:
        return
    st.caption("Seleccionado:")

    for cod, n in sorted(contador.items()):
        col1, col2, col3, col4 = st.columns([7, 2, 1, 1])
        with col1:
            desc = datos.get("etiquetas", {}).get(cod, cod)
            st.markdown(
                f"<div class='row'><strong>{cod}</strong> – "
                f"<span class='muted'>{_short(desc)}</span></div>",
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(f"<div class='count-pill'>× {n}</div>", unsafe_allow_html=True)
        with col3:
            if st.button("−", key=f"{state_key}_menos_{cod}", help="Quitar 1"):
                contador[cod] -= 1
                if contador[cod] <= 0:
                    del contador[cod]
                st.rerun()
        with col4:
            if st.button("🗑️", key=f"{state_key}_del_{cod}", help="Eliminar"):
                del contador[cod]
                st.rerun()


def _picker_con_cantidad(label: str, datos: dict, state_key: str, valores_previos: str = "") -> Counter:
    if not datos or not datos.get("valores"):
        st.info(f"No hay opciones para {label}.")
        return Counter()

    _scoped_css_once()

    if state_key not in st.session_state:
        st.session_state[state_key] = _parse_str_to_counter(valores_previos)

    contador: Counter = st.session_state[state_key]

    cols = st.columns([6, 2, 2])
    with cols[0]:
        codigo = st.selectbox(
            label,
            options=datos["valores"],
            format_func=lambda x: datos.get("etiquetas", {}).get(x, x),
            key=f"{state_key}_sel",
        )
    with cols[1]:
        qty = st.number_input(
            "Cantidad",
            min_value=1, value=1, step=1,
            key=f"{state_key}_qty",
            label_visibility="collapsed",
        )
    with cols[2]:
        if st.button("➕ Agregar", key=f"{state_key}_add", type="primary"):
            contador[str(codigo).strip().upper()] += int(qty)

    _render_lista(contador, datos, state_key)

    st.session_state[state_key] = contador
    return contador


# =============================================================================
# Componente principal
# =============================================================================
def crear_desplegables(opciones):
    """
    Devuelve dict para tu df_puntos (ancho):
      {'Poste': '2x PC-40', 'Primario': 'A-I-5', ...}
    """
    with st.container():
        st.markdown("<div class='xpicker'>", unsafe_allow_html=True)

        seleccion = {}
        df_actual = st.session_state.get("df_puntos", pd.DataFrame())
        punto_actual = st.session_state.get("punto_en_edicion")

        valores_previos = {}
        if (not df_actual.empty) and (punto_actual in df_actual.get("Punto", pd.Series(dtype=str)).values):
            fila = df_actual[df_actual["Punto"] == punto_actual].iloc[0].to_dict()
            valores_previos = {k: v for k, v in fila.items() if k != "Punto"}

        # Mezclar Conexiones a tierra + Protección
        cat_tierra = opciones.get("Conexiones a tierra", {"valores": [], "etiquetas": {}})
        cat_prot = opciones.get("Protección", {"valores": [], "etiquetas": {}})

        valores_mix = []
        vistos = set()
        for v in (cat_tierra.get("valores", []) + cat_prot.get("valores", [])):
            vv = str(v).strip()
            if vv and vv not in vistos:
                vistos.add(vv)
                valores_mix.append(vv)

        etiquetas_mix = {}
        etiquetas_mix.update(cat_tierra.get("etiquetas", {}) or {})
        etiquetas_mix.update(cat_prot.get("etiquetas", {}) or {})

        cat_tierra_prot = {"valores": valores_mix, "etiquetas": etiquetas_mix}

        col_izq, col_der = st.columns(2)

        with col_izq:
            c_poste = _picker_con_cantidad("Poste", opciones.get("Poste"), "cnt_poste", valores_previos.get("Poste", ""))
            c_sec = _picker_con_cantidad("Secundario", opciones.get("Secundario"), "cnt_sec", valores_previos.get("Secundario", ""))
            c_tierra = _picker_con_cantidad(
                "Conexiones a tierra / Protección",
                cat_tierra_prot,
                "cnt_tierra_prot",
                valores_previos.get("Conexiones a tierra", "")
            )

        with col_der:
            c_pri = _picker_con_cantidad("Primario", opciones.get("Primario"), "cnt_pri", valores_previos.get("Primario", ""))
            c_ret = _picker_con_cantidad("Retenidas", opciones.get("Retenidas"), "cnt_ret", valores_previos.get("Retenidas", ""))
            c_trf = _picker_con_cantidad("Transformadores", opciones.get("Transformadores"), "cnt_trf", valores_previos.get("Transformadores", ""))
            c_lum = _picker_con_cantidad("Luminarias", opciones.get("Luminarias"), "cnt_lum", valores_previos.get("Luminarias", ""))

        seleccion["Poste"] = _counter_to_str(c_poste)
        seleccion["Primario"] = _counter_to_str(c_pri)
        seleccion["Secundario"] = _counter_to_str(c_sec)
        seleccion["Retenidas"] = _counter_to_str(c_ret)
        seleccion["Conexiones a tierra"] = _counter_to_str(c_tierra)
        seleccion["Transformadores"] = _counter_to_str(c_trf)
        seleccion["Luminarias"] = _counter_to_str(c_lum)

        st.markdown("</div>", unsafe_allow_html=True)

    return seleccion



