# -*- coding: utf-8 -*-
# interfaz/estructuras_ui.py

from __future__ import annotations
from typing import Tuple
import streamlit as st
import pandas as pd

from entradas.estructuras import (
    inicializar_estado_estructuras,
    agregar_item_estructura,
    consolidar_punto,
    eliminar_punto,
    reset_estructuras,
    construir_dataframe_salida,
    crear_nuevo_punto,
)

# =========================================================
# DATA (DESDE ORQUESTADOR)
# =========================================================

def _obtener_opciones_desde_orquestador() -> dict:

    res_entradas = st.session_state.get("resultado_entradas")

    if not res_entradas or not hasattr(res_entradas, "base_datos"):
        return {}

    df_indice = res_entradas.base_datos.get("INDICE", pd.DataFrame())

    if df_indice.empty or "CODIGO" not in df_indice.columns:
        return {}

    df_indice = df_indice.copy()
    df_indice.columns = df_indice.columns.str.strip().str.upper()

    def clasificar(c):
        c = str(c).upper()
        if c.startswith("PC"): return "Poste"
        elif c.startswith("A-"): return "Primario"
        elif c.startswith("B-"): return "Secundario"
        elif c.startswith("R-"): return "Retenidas"
        elif c.startswith("CA") or c.startswith("CS") or c.startswith("CT"): return "Conexiones a tierra"
        elif c.startswith("TS"): return "Transformadores"
        elif c.startswith("LL"): return "Luminarias"
        return "Otros"

    df_indice["CATEGORIA"] = df_indice["CODIGO"].apply(clasificar)

    opciones = {}

    for cat, g in df_indice.groupby("CATEGORIA"):
        opciones[cat] = {
            "valores": sorted(g["CODIGO"].dropna().unique().tolist()),
            "etiquetas": {
                row["CODIGO"]: row.get("ESTRUCTURA", row["CODIGO"])
                for _, row in g.iterrows()
            }
        }

    return opciones


# =========================================================
# UI HELPERS
# =========================================================

def _fila_categoria_ui(cat_key, valores, etiquetas, key_prefix):

    st.markdown(f"**{cat_key}**")

    c1, c2, c3 = st.columns([7, 1.2, 2])

    with c1:
        sel = st.selectbox(
            "",
            valores if valores else [""],
            index=0,
            key=f"{key_prefix}_{cat_key}_sel",
            label_visibility="collapsed",
            format_func=lambda x: etiquetas.get(x, x),
        )

    with c2:
        st.number_input(
            "",
            min_value=1,
            max_value=99,
            step=1,
            value=1,
            key=f"{key_prefix}_{cat_key}_qty",
            label_visibility="collapsed",
        )

    with c3:
        if st.button("➕", key=f"{key_prefix}_{cat_key}_add"):
            if sel:
                punto = st.session_state.get("punto_en_edicion", "Punto 1")
                agregar_item_estructura(punto, sel)


# =========================================================
# UI PRINCIPAL
# =========================================================

def seccion_entrada_estructuras() -> Tuple[pd.DataFrame | None, str | None]:

    inicializar_estado_estructuras()

    # 🔥 OPCIONES DESDE ORQUESTADOR
    opciones = _obtener_opciones_desde_orquestador()

    st.subheader("🏗️ Estructuras del Proyecto")

    # 🔎 DEBUG SUAVE (no rompe nada)
    if not opciones:
        st.warning("⚠️ No se pudo cargar catálogo desde base_datos (INDICE)")

    df_actual = st.session_state.get("df_puntos", pd.DataFrame())

    # =====================================================
    # CONTROLES
    # =====================================================
    colA, colB, colC, colD = st.columns([1.2, 1.4, 1.8, 1.2])

    with colA:
        if st.button("🆕 Punto"):
            crear_nuevo_punto()

    with colB:
        if not df_actual.empty:
            p_sel = st.selectbox("Ir a:", df_actual["Punto"].unique())
            if st.button("Editar"):
                st.session_state["punto_en_edicion"] = p_sel

    with colC:
        if not df_actual.empty:
            p_del = st.selectbox("Eliminar:", df_actual["Punto"].unique())
            if st.button("Borrar"):
                eliminar_punto(p_del)

    with colD:
        if st.button("🧹 Reset"):
            reset_estructuras()

    punto = st.session_state.get("punto_en_edicion", "Punto 1")
    st.markdown(f"### {punto}")

    # =====================================================
    # CATEGORÍAS
    # =====================================================
    categorias = [
        "Poste",
        "Primario",
        "Secundario",
        "Retenidas",
        "Conexiones a tierra",
        "Transformadores",
        "Luminarias",
    ]

    kp = f"kp_{punto}"

    for cat in categorias:
        valores = opciones.get(cat, {}).get("valores", [])
        etiquetas = opciones.get(cat, {}).get("etiquetas", {})
        _fila_categoria_ui(cat, valores, etiquetas, kp)

    # =====================================================
    # VISTA PREVIA
    # =====================================================
    fila = consolidar_punto(punto)
    st.dataframe(pd.DataFrame([fila]), use_container_width=True, hide_index=True)

    # =====================================================
    # GUARDAR (🔥 SOLO UI)
    # =====================================================
    if st.button("💾 Guardar"):

        df, ruta = construir_dataframe_salida()

        if df is None or df.empty:
            st.warning("No hay estructuras para guardar")
            return None, None

        st.session_state["df_estructuras"] = df

        st.success("✅ Estructuras guardadas correctamente")

        return df, ruta

    # =====================================================
    # SALIDA FINAL
    # =====================================================
    return None, None
