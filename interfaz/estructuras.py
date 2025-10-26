# -*- coding: utf-8 -*-
# interfaz/estructuras.py

from __future__ import annotations
import pandas as pd
import streamlit as st

from interfaz.base import COLUMNAS_BASE, resetear_desplegables
from modulo.utils import guardar_archivo_temporal, pegar_texto_a_df
from modulo.entradas import cargar_estructuras_proyectadas


# ==============================
# Modo: cargar desde Excel
# ==============================
def cargar_desde_excel():
    archivo_estructuras = st.file_uploader("Archivo de estructuras", type=["xlsx"], key="upl_estructuras")
    if archivo_estructuras:
        ruta_estructuras = guardar_archivo_temporal(archivo_estructuras)
        try:
            df = cargar_estructuras_proyectadas(ruta_estructuras)
            st.success("✅ Hoja 'estructuras' leída correctamente")
            return df, ruta_estructuras
        except Exception as e:
            st.error(f"❌ No se pudo leer la hoja 'estructuras': {e}")
    return pd.DataFrame(columns=COLUMNAS_BASE), None


# ==============================
# Modo: pegar tabla
# ==============================
def pegar_tabla():
    texto_pegado = st.text_area("Pega aquí tu tabla CSV/tabulado", height=200, key="txt_pegar_tabla")
    if texto_pegado:
        df = pegar_texto_a_df(texto_pegado, COLUMNAS_BASE)
        st.success(f"✅ Tabla cargada con {len(df)} filas")
        return df
    return pd.DataFrame(columns=COLUMNAS_BASE)


# =========================================================
# MODELO: Estado por punto
# =========================================================
def _init_punto_state():
    if "df_puntos" not in st.session_state:
        st.session_state["df_puntos"] = pd.DataFrame(columns=COLUMNAS_BASE)

    if "punto_en_edicion" not in st.session_state or not st.session_state["punto_en_edicion"]:
        df = st.session_state["df_puntos"]
        st.session_state["punto_en_edicion"] = df["Punto"].iloc[0] if not df.empty else "Punto 1"

    if "puntos_data" not in st.session_state:
        st.session_state["puntos_data"] = {}

    p = st.session_state["punto_en_edicion"]
    if p not in st.session_state["puntos_data"]:
        st.session_state["puntos_data"][p] = {
            "Poste": {}, "Primario": {}, "Secundario": {},
            "Retenidas": {}, "Conexiones a tierra": {}, "Transformadores": {}
        }


def add_item(categoria: str, codigo: str, cantidad: int = 1):
    if not codigo:
        return
    p = st.session_state["punto_en_edicion"]
    bucket = st.session_state["puntos_data"][p][categoria]
    bucket[codigo] = bucket.get(codigo, 0) + cantidad


def render_cat_str(punto: str, categoria: str) -> str:
    data = st.session_state["puntos_data"][punto][categoria]
    if not data:
        return ""
    return ", ".join(
        f"{n}× {code}" if n > 1 else code
        for code, n in data.items()
    )


# ===========================
# NECESARIO AQUÍ (ANTES QUE _fila_agregar)
# ===========================
def _opciones_categoria(opciones_dict, llave_catalogo: str) -> tuple[list[str], dict]:
    bloque = opciones_dict.get(llave_catalogo) or {}
    valores = bloque.get("valores", []) or []
    etiquetas = bloque.get("etiquetas", {}) or {}
    return valores, etiquetas


def _val_or_dash(s): return s if (s and str(s).strip()) else "-"


def _consolidado_a_fila(p: str) -> dict:
    return {
        "Punto": p,
        "Poste": _val_or_dash(render_cat_str(p, "Poste")),
        "Primario": _val_or_dash(render_cat_str(p, "Primario")),
        "Secundario": _val_or_dash(render_cat_str(p, "Secundario")),
        "Retenidas": _val_or_dash(render_cat_str(p, "Retenidas")),
        "Conexiones a tierra": _val_or_dash(render_cat_str(p, "Conexiones a tierra")),
        "Transformadores": _val_or_dash(render_cat_str(p, "Transformadores")),
    }


# =========================================================
# UI Componentes (Refactor)
# =========================================================
def _barra_puntos(df_actual):
    colA, colB, colC, colD = st.columns([1.2, 1.2, 1.8, 1.2])

    with colA:
        if st.button("🆕 Crear nuevo Punto"):
            existentes = df_actual["Punto"].unique().tolist() if not df_actual.empty else []
            nums = [int("".join(filter(str.isdigit, p))) for p in existentes if any(c.isdigit() for c in p)]
            nuevo = f"Punto {(max(nums) + 1) if nums else 1}"

            st.session_state["punto_en_edicion"] = nuevo
            st.session_state["puntos_data"][nuevo] = {
                "Poste": {}, "Primario": {}, "Secundario": {},
                "Retenidas": {}, "Conexiones a tierra": {}, "Transformadores": {}
            }
            st.success(f"✏️ {nuevo} listo para editar")
            resetear_desplegables()

    with colB:
        if not df_actual.empty:
            p_sel = st.selectbox("📍 Ir a punto:", df_actual["Punto"].unique(), key="sel_goto")
            if st.button("✏️ Editar", key="btn_edit"):
                st.session_state["punto_en_edicion"] = p_sel
                resetear_desplegables()

    with colC:
        if not df_actual.empty:
            p_del = st.selectbox("❌ Borrar punto:", df_actual["Punto"].unique(), key="sel_del")
            if st.button("Borrar", key="btn_del"):
                st.session_state["df_puntos"] = df_actual[df_actual["Punto"] != p_del].reset_index(drop=True)
                st.session_state["puntos_data"].pop(p_del, None)
                st.success("✅ Se eliminó")

    with colD:
        if st.button("🧹 Limpiar todo"):
            st.session_state["df_puntos"] = pd.DataFrame(columns=COLUMNAS_BASE)
            st.session_state["puntos_data"].clear()
            st.session_state["punto_en_edicion"] = "Punto 1"
            _init_punto_state()
            st.success("✅ Todo limpio")


def _fila_agregar(opciones):
    cats = {
        "Poste":              _opciones_categoria(opciones, "Poste"),
        "Primario":           _opciones_categoria(opciones, "Primario"),
        "Secundario":         _opciones_categoria(opciones, "Secundario"),
        "Retenidas":          _opciones_categoria(opciones, "Retenidas"),
        "Conexiones a tierra": _opciones_categoria(opciones, "Conexiones a tierra"),
        "Transformadores":     _opciones_categoria(opciones, "Transformadores"),
    }

    cols = st.columns([2,2,2,2,2,2,1])
    keys = ["poste_sel","prim_sel","sec_sel","ret_sel","tierra_sel","tr_sel"]

    for i, (cat, (vals, labs)) in enumerate(cats.items()):
        with cols[i]:
            st.session_state[keys[i]] = st.selectbox(
                cat,
                [""] + vals,
                format_func=lambda x, labs=labs: labs.get(x, x),
                key=keys[i]
            )

    with cols[6]:
        if st.button("➕", key="add_all", type="primary"):
            for i, cat in enumerate(cats.keys()):
                sel = st.session_state.get(keys[i])
                if sel:
                    add_item(cat, sel, 1)

            for k in keys:
                st.session_state.pop(k, None)

            st.success("✅ ¡Agregado!")
            st.rerun()


def _vista_guardar():
    p = st.session_state["punto_en_edicion"]
    data_row = _consolidado_a_fila(p)

    st.dataframe(pd.DataFrame([data_row]), use_container_width=True, hide_index=True)

    if st.button("💾 Guardar punto", type="primary"):
        df = st.session_state["df_puntos"]
        df = df[df["Punto"] != p]
        st.session_state["df_puntos"] = pd.concat([df, pd.DataFrame([data_row])], ignore_index=True)
        st.success("✅ Guardado!")

    df_all = st.session_state["df_puntos"]
    if not df_all.empty:
        st.dataframe(df_all, use_container_width=True, hide_index=True)


# =========================================================
# Controlador
# =========================================================
def listas_desplegables():
    from modulo.desplegables import cargar_opciones
    opciones = cargar_opciones()

    st.subheader("3. 🏗️ Estructuras del Proyecto")
    _init_punto_state()
    df_actual = st.session_state["df_puntos"]

    _barra_puntos(df_actual)
    st.markdown("---")

    p = st.session_state["punto_en_edicion"]
    st.markdown(f"### ✏️ Editando {p}")
    st.markdown("#### ➕ Agregar estructuras a este punto")
    _fila_agregar(opciones)

    st.markdown("---")
    _vista_guardar()

    return st.session_state["df_puntos"]


# ==============================
# Despachador
# ==============================
def seccion_entrada_estructuras(modo_carga: str):
    df, ruta = pd.DataFrame(columns=COLUMNAS_BASE), None

    if modo_carga == "Desde archivo Excel":
        df, ruta = cargar_desde_excel()
    elif modo_carga == "Pegar tabla":
        df = pegar_tabla()
    elif modo_carga == "Listas desplegables":
        df = listas_desplegables()

    return df, ruta
