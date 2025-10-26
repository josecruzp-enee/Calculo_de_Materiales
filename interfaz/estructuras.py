# -*- coding: utf-8 -*-
# interfaz/estructuras.py

from __future__ import annotations
import pandas as pd
import streamlit as st

from interfaz.base import COLUMNAS_BASE, resetear_desplegables
from modulo.utils import guardar_archivo_temporal, pegar_texto_a_df
from modulo.entradas import cargar_estructuras_proyectadas


# ===============================================
# MODO: Desde Excel
# ===============================================
def cargar_desde_excel():
    archivo_estructuras = st.file_uploader("Archivo de estructuras", type=["xlsx"], key="upl_estructuras")
    if archivo_estructuras:
        ruta_estructuras = guardar_archivo_temporal(archivo_estructuras)
        try:
            df = cargar_estructuras_proyectadas(ruta_estructuras)
            st.success("✅ Hoja 'estructuras' cargada")
            return df, ruta_estructuras
        except Exception as e:
            st.error(f"❌ Error: {e}")
    return pd.DataFrame(columns=COLUMNAS_BASE), None


# ===============================================
# MODO: Pegar tabla
# ===============================================
def pegar_tabla():
    texto = st.text_area("Pega aquí tu tabla CSV/tabulado", height=200)
    if texto:
        df = pegar_texto_a_df(texto, COLUMNAS_BASE)
        st.success(f"✅ {len(df)} filas cargadas")
        return df
    return pd.DataFrame(columns=COLUMNAS_BASE)


# =========================================================
# MODELO: Estado Consolidado por Punto
# =========================================================
def _init_punto_state():
    if "df_puntos" not in st.session_state:
        st.session_state["df_puntos"] = pd.DataFrame(columns=COLUMNAS_BASE)

    if "punto_en_edicion" not in st.session_state:
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


def add_item(cat, code):
    if not code:
        return
    p = st.session_state["punto_en_edicion"]
    cnt = st.session_state["puntos_data"][p][cat]
    cnt[code] = cnt.get(code, 0) + 1


def render_cat_str(p, cat):
    data = st.session_state["puntos_data"][p][cat]
    if not data:
        return ""
    return ", ".join(f"{n}× {c}" if n > 1 else c for c, n in data.items())


def _val_or_dash(v): return v if v.strip() else "-"


def _fila_dict(p):
    return {
        "Punto": p,
        "Poste": _val_or_dash(render_cat_str(p, "Poste")),
        "Primario": _val_or_dash(render_cat_str(p, "Primario")),
        "Secundario": _val_or_dash(render_cat_str(p, "Secundario")),
        "Retenidas": _val_or_dash(render_cat_str(p, "Retenidas")),
        "Conexiones a tierra": _val_or_dash(render_cat_str(p, "Conexiones a tierra")),
        "Transformadores": _val_or_dash(render_cat_str(p, "Transformadores")),
    }


def _opciones_categoria(opciones, key):
    obj = opciones.get(key, {})
    return obj.get("valores", []), obj.get("etiquetas", {})


# =========================================================
# UI: Barra de control de puntos
# =========================================================
def _barra_puntos(df_actual):
    colA, colB, colC, colD = st.columns([1.2, 1.2, 1.8, 1.2])

    with colA:
        if st.button("🆕 Punto nuevo"):
            existentes = df_actual["Punto"].unique().tolist() if not df_actual.empty else []
            nums = [int("".join(filter(str.isdigit, p))) for p in existentes if any(c.isdigit() for c in p)]
            nuevo = f"Punto {(max(nums) + 1) if nums else 1}"
            st.session_state["punto_en_edicion"] = nuevo
            st.session_state["puntos_data"][nuevo] = {
                "Poste": {}, "Primario": {}, "Secundario": {},
                "Retenidas": {}, "Conexiones a tierra": {}, "Transformadores": {}
            }
            resetear_desplegables()
            st.success(f"📍 {nuevo} creado")

    with colB:
        if not df_actual.empty:
            p_sel = st.selectbox("Ir a:", df_actual["Punto"].unique(), key="goto")
            if st.button("✏️ Editar"):
                st.session_state["punto_en_edicion"] = p_sel
                resetear_desplegables()

    with colC:
        if not df_actual.empty:
            p_del = st.selectbox("Eliminar:", df_actual["Punto"].unique(), key="del")
            if st.button("🗑 Borrar"):
                st.session_state["df_puntos"] = df_actual[df_actual["Punto"] != p_del]
                st.session_state["puntos_data"].pop(p_del, None)
                st.success("✅ Eliminado")

    with colD:
        if st.button("🧹 Limpiar todo"):
            st.session_state["df_puntos"] = pd.DataFrame(columns=COLUMNAS_BASE)
            st.session_state["puntos_data"] = {}
            st.session_state["punto_en_edicion"] = "Punto 1"
            _init_punto_state()
            resetear_desplegables()
            st.success("✅ Todo limpio")


# =========================================================
# UI: Fila de selects para agregar estructuras
# =========================================================
def _fila_agregar(opciones):
    p = st.session_state["punto_en_edicion"]

    cats = [
        ("Poste", "poste_sel"),
        ("Primario", "prim_sel"),
        ("Secundario", "sec_sel"),
        ("Retenidas", "ret_sel"),
        ("Conexiones a tierra", "tierra_sel"),
        ("Transformadores", "tr_sel")
    ]

    cols = st.columns([2,2,2,2,2,2,1])

    # Dibujar selects (se limpian automáticamente cuando el key no existe)
    for i, (cat, key) in enumerate(cats):
        vals,labs=_opciones_categoria(opciones,cat)
        with cols[i]:
            st.selectbox(cat,[""]+vals,format_func=lambda x,l=labs: l.get(x,x),key=key)

    with cols[6]:
        if st.button("➕"):
            for cat,key in cats:
                sel = st.session_state.get(key,"")
                if sel:
                    add_item(cat, sel)

            st.session_state["limpiar_selects"]=True
            st.success("✅ Agregado")


# =========================================================
# UI: Vista del punto + guardar
# =========================================================
def _vista_y_guardar():
    p = st.session_state["punto_en_edicion"]
    fila = _fila_dict(p)
    st.dataframe(pd.DataFrame([fila]), use_container_width=True, hide_index=True)

    if st.button("💾 Guardar punto", type="primary"):
        df = st.session_state["df_puntos"]
        df = df[df["Punto"] != p]
        st.session_state["df_puntos"] = pd.concat([df,pd.DataFrame([fila])], ignore_index=True)
        st.success("✅ Guardado!")

    df_all = st.session_state["df_puntos"]
    if not df_all.empty:
        st.dataframe(df_all, use_container_width=True, hide_index=True)


# =========================================================
# Controlador principal del modo desplegables
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
    st.markdown(f"✏️ Editando {p}")
    _fila_agregar(opciones)

    # ✅ Limpieza SEGURA de selects
    if st.session_state.get("limpiar_selects", False):
        for k in ["poste_sel","prim_sel","sec_sel","ret_sel","tierra_sel","tr_sel"]:
            st.session_state.pop(k, None)
        st.session_state["limpiar_selects"]=False
        st.rerun()

    st.markdown("---")
    _vista_y_guardar()

    return st.session_state["df_puntos"]


# =========================================================
# Despachador según modo ingreso
# =========================================================
def seccion_entrada_estructuras(modo_carga: str):
    if modo_carga == "Desde archivo Excel":
        return cargar_desde_excel()
    elif modo_carga == "Pegar tabla":
        return pegar_tabla(), None
    elif modo_carga == "Listas desplegables":
        return listas_desplegables(), None

    return pd.DataFrame(columns=COLUMNAS_BASE), None
