# interfaz/estructuras_ui.py
# SOLO UI — SIN LÓGICA DE NEGOCIO

from __future__ import annotations
from typing import Tuple
import streamlit as st
import pandas as pd

from dominio.entradas.estructuras import (
    inicializar_estado_estructuras,
    obtener_opciones_catalogo,
    agregar_item_estructura,
    consolidar_punto,
    eliminar_punto,
    reset_estructuras,
    construir_dataframe_salida,
    crear_nuevo_punto,   # 👈 NUEVO (dominio)
)


# =========================================================
# UI HELPERS
# =========================================================

def _fila_categoria_ui(cat_key, valores, etiquetas, key_prefix):

    st.markdown(f"**{cat_key}**")

    c1, c2, c3 = st.columns([7, 1.2, 2])

    with c1:
        sel = st.selectbox(
            "",
            valores if valores else [""],   # 🔥 evita error
            index=0,
            key=f"{key_prefix}_{cat_key}_sel",
            label_visibility="collapsed",
            format_func=lambda x: etiquetas.get(x, x),
        )

    with c2:
        qty = st.number_input(
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
            if sel:  # 🔥 evita agregar vacío
                agregar_item_estructura(cat_key, sel, qty)


# =========================================================
# UI PRINCIPAL
# =========================================================

def seccion_entrada_estructuras() -> Tuple[pd.DataFrame | None, str | None]:
    """
    UI pura para estructuras.
    """

    inicializar_estado_estructuras()
    opciones = obtener_opciones_catalogo()

    st.subheader("🏗️ Estructuras del Proyecto")

    df_actual = st.session_state.get("df_puntos", pd.DataFrame())

    # =====================================================
    # CONTROLES
    # =====================================================
    colA, colB, colC, colD = st.columns([1.2, 1.4, 1.8, 1.2])

    with colA:
        if st.button("🆕 Punto"):
            crear_nuevo_punto()   # 🔥 dominio maneja lógica

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
    # GUARDAR
    # =====================================================
    guardar = st.button("💾 Guardar")

    if guardar:
        df, ruta = construir_dataframe_salida(punto)
        st.success("Estructura guardada")
        return df, ruta

    # =====================================================
    # SALIDA FINAL (SIN REGENERAR)
    # =====================================================
    return None, None
