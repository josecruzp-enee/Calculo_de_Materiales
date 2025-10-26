# modulo/desplegables.py
# -*- coding: utf-8 -*-

import os
from collections import Counter
import pandas as pd
import streamlit as st

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
RUTA_EXCEL = os.path.join(REPO_ROOT, "data", "Estructura_datos.xlsx")


# ---------------------------
# Cargar opciones desde "indice"
# ---------------------------
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

    # Normaliza nombres a los que ya usas en tu UI
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


# ---------------------------
# Helpers de conteo <-> string
# ---------------------------
def _parse_str_to_counter(s: str) -> Counter:
    """
    Acepta:
      - "R-1 , R-1 , B-II-4C"
      - "R-1 + R-1 + B-II-4C"
      - "2x R-1 , 1x B-II-4C"
    y devuelve Counter({'R-1': 2, 'B-II-4C': 1})
    """
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


# ---------------------------
# Picker con cantidad (permite duplicados)
# ---------------------------
def _picker_con_cantidad(label: str, datos: dict, state_key: str, valores_previos: str = "") -> Counter:
    """
    Select + number + “Agregar” que acumula en un Counter en session_state[state_key].
    Mantiene tu look & feel (sin CSS global): usa columnas y botones estándar.
    """
    if not datos:
        st.info(f"No hay opciones para {label}.")
        return Counter()

    # Estado inicial: si estamos editando, partir de lo que ya hay guardado
    if state_key not in st.session_state:
        st.session_state[state_key] = _parse_str_to_counter(valores_previos)

    contador: Counter = st.session_state[state_key]

    # Barra compacta: Select | Cantidad | ➕
    cols = st.columns([6, 2, 2])
    with cols[0]:
        codigo = st.selectbox(
            label,
            options=datos["valores"],
            format_func=lambda x: datos["etiquetas"].get(x, x),
            key=f"{state_key}_sel"
        )
    with cols[1]:
        qty = st.number_input("Cantidad", min_value=1, value=1, step=1, key=f"{state_key}_qty")
    with cols[2]:
        if st.button("➕ Agregar", key=f"{state_key}_add"):
            contador[codigo] += qty

    # Resumen con acciones por fila (− / ×n / Eliminar)
    if contador:
        st.caption("Seleccionado:")
        for cod, n in sorted(contador.items()):
            a, b, c, d = st.columns([6, 2, 2, 2])
            with a:
                st.write(datos["etiquetas"].get(cod, cod))
            with b:
                if st.button("−", key=f"{state_key}_menos_{cod}") and n > 1:
                    contador[cod] -= 1
                    if contador[cod] <= 0:
                        del contador[cod]
                    st.rerun()
            with c:
                st.write(f"× {n}")
            with d:
                if st.button("Eliminar", key=f"{state_key}_del_{cod}"):
                    del contador[cod]
                    st.rerun()

    st.session_state[state_key] = contador
    return contador


# ---------------------------
# UI principal (se usa en interfaz/estructuras.py)
# ---------------------------
def crear_desplegables(opciones):
    """
    Devuelve un dict listo para guardar en df_puntos (mismo formato que usabas):
      {'Poste': '2x PC-40', 'Primario': 'A-I-5', ...}
    """
    seleccion = {}
    df_actual = st.session_state.get("df_puntos", pd.DataFrame())
    punto_actual = st.session_state.get("punto_en_edicion")

    # Valores previos para “editar punto”
    valores_previos = {}
    if not df_actual.empty and punto_actual in df_actual.get("Punto", pd.Series(dtype=str)).values:
        fila = df_actual[df_actual["Punto"] == punto_actual].iloc[0].to_dict()
        valores_previos = {k: v for k, v in fila.items() if k != "Punto"}

    # Dos columnas, como tu UI
    col_izq, col_der = st.columns(2)
    with col_izq:
        c_poste = _picker_con_cantidad("Poste", opciones.get("Poste"), "cnt_poste", valores_previos.get("Poste", ""))
        c_sec   = _picker_con_cantidad("Secundario", opciones.get("Secundario"), "cnt_sec", valores_previos.get("Secundario", ""))
        c_tierra= _picker_con_cantidad("Conexiones a tierra", opciones.get("Conexiones a tierra"), "cnt_tierra", valores_previos.get("Conexiones a tierra", ""))

    with col_der:
        c_pri   = _picker_con_cantidad("Primario", opciones.get("Primario"), "cnt_pri", valores_previos.get("Primario", ""))
        c_ret   = _picker_con_cantidad("Retenidas", opciones.get("Retenidas"), "cnt_ret", valores_previos.get("Retenidas", ""))
        c_trf   = _picker_con_cantidad("Transformadores", opciones.get("Transformadores"), "cnt_trf", valores_previos.get("Transformadores", ""))

    # Convertir los counters a texto (el mismo formato que ya persistes)
    seleccion["Poste"]               = _counter_to_str(c_poste)
    seleccion["Primario"]            = _counter_to_str(c_pri)
    seleccion["Secundario"]          = _counter_to_str(c_sec)
    seleccion["Retenidas"]           = _counter_to_str(c_ret)
    seleccion["Conexiones a tierra"] = _counter_to_str(c_tierra)
    seleccion["Transformadores"]     = _counter_to_str(c_trf)

    return seleccion
