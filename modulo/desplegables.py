# modulo/desplegables.py
# -*- coding: utf-8 -*-

import os
from collections import Counter
import pandas as pd
import streamlit as st

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
RUTA_EXCEL = os.path.join(REPO_ROOT, "data", "Estructura_datos.xlsx")


# ========== Cargar catálogo desde "indice" ==========
def cargar_opciones():
    df = pd.read_excel(RUTA_EXCEL, sheet_name="indice")
    df.columns = df.columns.str.strip()

    clas_col = "Clasificación" if "Clasificación" in df.columns else "Clasificacion"
    cod_col  = "Código de Estructura" if "Código de Estructura" in df.columns else "Codigo de Estructura"
    desc_col = "Descripción" if "Descripción" in df.columns else "Descripcion"

    opciones = {}
    for clasificacion in df[clas_col].dropna().unique():
        subset = df[df[clas_col] == clasificacion]
        codigos = subset[cod_col].dropna().astype(str).tolist()
        etiquetas = {
            str(row[cod_col]): f"{row[cod_col]} – {row[desc_col]}"
            for _, row in subset.iterrows()
            if pd.notna(row[cod_col])
        }
        opciones[clasificacion] = {"valores": codigos, "etiquetas": etiquetas}

    # normaliza nombres a los usados en tu UI
    mapping = {
        "Poste": "Poste",
        "Primaria": "Primario",
        "Secundaria": "Secundario",
        "Retenidas": "Retenidas",
        "Conexiones a tierra": "Conexiones a tierra",
        "Transformadores": "Transformadores",
    }
    normalizado = {}
    for k, v in opciones.items():
        normalizado[mapping.get(k, k)] = v
    return normalizado


# ========== Helpers de parseo (2x R-1  <->  Counter) ==========
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


# ========== UI: picker con cantidad (bonito y compacto) ==========
def _scoped_css_once():
    if st.session_state.get("_xpicker_css", False):
        return
    st.session_state["_xpicker_css"] = True
    st.markdown(
        """
        <style>
        /* Estilos SOLO dentro de .xpicker para no tocar tu tema global */
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
    """Lista bonita con código, descripción corta, cantidad (píldora) y acciones."""
    if not contador:
        return
    st.caption("Seleccionado:")

    for cod, n in sorted(contador.items()):
        col1, col2, col3, col4 = st.columns([7, 2, 1, 1])
        with col1:
            desc = datos["etiquetas"].get(cod, cod)
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
    """
    Línea compacta: Select | Cantidad | ➕ Agregar
    + lista seleccionada con píldoras y acciones.
    """
    if not datos:
        st.info(f"No hay opciones para {label}.")
        return Counter()

    _scoped_css_once()

    # Estado inicial (si vienes de "Editar Punto")
    if state_key not in st.session_state:
        st.session_state[state_key] = _parse_str_to_counter(valores_previos)

    contador: Counter = st.session_state[state_key]

    # Picker compacto
    cols = st.columns([6, 2, 2])
    with cols[0]:
        codigo = st.selectbox(
            label,
            options=datos["valores"],
            format_func=lambda x: datos["etiquetas"].get(x, x),
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
            contador[codigo] += qty

    _render_lista(contador, datos, state_key)

    st.session_state[state_key] = contador
    return contador


# ========== Componente principal que usa interfaz/estructuras.py ==========
def crear_desplegables(opciones):
    """
    Devuelve un dict igual al que ya guardas en df_puntos:
      {'Poste': '2x PC-40', 'Primario': 'A-I-5', ...}
    """
    with st.container():  # scope para el CSS local
        st.markdown("<div class='xpicker'>", unsafe_allow_html=True)

        seleccion = {}
        df_actual = st.session_state.get("df_puntos", pd.DataFrame())
        punto_actual = st.session_state.get("punto_en_edicion")

        # Valores previos si se está editando
        valores_previos = {}
        if not df_actual.empty and punto_actual in df_actual.get("Punto", pd.Series(dtype=str)).values:
            fila = df_actual[df_actual["Punto"] == punto_actual].iloc[0].to_dict()
            valores_previos = {k: v for k, v in fila.items() if k != "Punto"}

        # Estructura en dos columnas (como tu layout)
        col_izq, col_der = st.columns(2)
        with col_izq:
            c_poste = _picker_con_cantidad("Poste", opciones.get("Poste"), "cnt_poste", valores_previos.get("Poste", ""))
            c_sec   = _picker_con_cantidad("Secundario", opciones.get("Secundario"), "cnt_sec", valores_previos.get("Secundario", ""))
            c_tierra= _picker_con_cantidad("Conexiones a tierra", opciones.get("Conexiones a tierra"), "cnt_tierra", valores_previos.get("Conexiones a tierra", ""))

        with col_der:
            c_pri   = _picker_con_cantidad("Primario", opciones.get("Primario"), "cnt_pri", valores_previos.get("Primario", ""))
            c_ret   = _picker_con_cantidad("Retenidas", opciones.get("Retenidas"), "cnt_ret", valores_previos.get("Retenidas", ""))
            c_trf   = _picker_con_cantidad("Transformadores", opciones.get("Transformadores"), "cnt_trf", valores_previos.get("Transformadores", ""))

        # Salida final en el formato que ya consume tu app
        seleccion["Poste"]               = _counter_to_str(c_poste)
        seleccion["Primario"]            = _counter_to_str(c_pri)
        seleccion["Secundario"]          = _counter_to_str(c_sec)
        seleccion["Retenidas"]           = _counter_to_str(c_ret)
        seleccion["Conexiones a tierra"] = _counter_to_str(c_tierra)
        seleccion["Transformadores"]     = _counter_to_str(c_trf)

        st.markdown("</div>", unsafe_allow_html=True)

    return seleccion
