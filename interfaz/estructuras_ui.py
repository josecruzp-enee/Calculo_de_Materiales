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
# DATA (CATÁLOGO)
# =========================================================

from entradas.base_datos import cargar_base_datos


def _obtener_opciones_desde_orquestador() -> dict:

    try:
        base_datos = cargar_base_datos()
        df_indice = base_datos.get("INDICE", pd.DataFrame())
    except:
        return {}

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
            format_func=lambda x: f"{x} - {etiquetas.get(x, '')}",
        )

        # 🔥 mostrar selección actual
        if sel:
            st.caption(f"Seleccionado: {sel}")

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
            if sel:
                punto = st.session_state.get("punto_en_edicion", "P-01")

                for _ in range(qty):
                    agregar_item_estructura(punto, sel)

                st.success(f"✔ {sel} agregado a {punto}")

# =========================================================
# UI PRINCIPAL
# =========================================================

def seccion_entrada_estructuras() -> Tuple[pd.DataFrame | None, str | None]:

    inicializar_estado_estructuras()

    opciones = _obtener_opciones_desde_orquestador()

    st.subheader("🏗️ Estructuras del Proyecto")

    if not opciones:
        st.warning("⚠️ No se pudo cargar catálogo desde base_datos (INDICE)")

    df_hist = st.session_state.get("df_puntos", pd.DataFrame())

    # =====================================================
    # CONTROLES
    # =====================================================
    colA, colB, colC, colD = st.columns([1.2, 1.4, 1.8, 1.2])

    with colA:
        if st.button("🆕 Punto"):
            crear_nuevo_punto()
            st.success(f"Creando {st.session_state.get('punto_en_edicion')}")

    with colB:
        if not df_hist.empty:
            p_sel = st.selectbox("Ir a:", df_hist["Punto"].unique())
            if st.button("Editar"):
                st.session_state["punto_en_edicion"] = p_sel

    with colC:
        if not df_hist.empty:
            p_del = st.selectbox("Eliminar:", df_hist["Punto"].unique())
            if st.button("Borrar"):
                eliminar_punto(p_del)

    with colD:
        if st.button("🧹 Reset"):
            reset_estructuras()

    # =====================================================
    # PUNTO ACTUAL
    # =====================================================
    punto = st.session_state.get("punto_en_edicion", "P-01")
    st.markdown(f"### {punto}")

    # =====================================================
    # 🔥 ESTRUCTURAS DEL PUNTO ACTUAL
    # =====================================================
    df_punto = df_hist[df_hist["Punto"] == punto]

    st.divider()

    if not df_punto.empty:
        st.markdown("### 📌 Estructuras en este punto")
        st.dataframe(df_punto, use_container_width=True, hide_index=True)
    else:
        st.info("Este punto aún no tiene estructuras")

    # =====================================================
    # 🔥 RESUMEN DEL PUNTO
    # =====================================================
    fila_actual = consolidar_punto(punto)

    if fila_actual and fila_actual.get("Estructuras"):
        st.markdown("### 🧾 Resumen del punto")

        df_sel = pd.DataFrame({
            "Estructura": fila_actual["Estructuras"]
        })

        st.dataframe(df_sel, use_container_width=True, hide_index=True)

    # =====================================================
    # 🔥 HISTÓRICO DE PUNTOS
    # =====================================================
    if not df_hist.empty:

        st.divider()
        st.markdown("### 📍 Puntos guardados")

        df_hist_temp = df_hist.copy()

        df_hist_temp["orden"] = (
            df_hist_temp["Punto"]
            .astype(str)
            .str.extract(r'(\d+)')[0]
            .astype(float)
        )

        df_hist_temp = df_hist_temp.sort_values("orden").drop(columns=["orden"])

        st.dataframe(df_hist_temp, use_container_width=True, hide_index=True)

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
    # VISTA PREVIA FINAL
    # =====================================================
    fila = consolidar_punto(punto)

    st.divider()
    st.markdown("### 📊 Vista previa")

    st.dataframe(
        pd.DataFrame([fila]),
        use_container_width=True,
        hide_index=True
    )

    # =====================================================
    # GUARDAR
    # =====================================================
    if st.button("💾 Guardar"):

        df, ruta = construir_dataframe_salida()

        if df is None or df.empty:
            st.warning("No hay estructuras para guardar")
            return None, None

        st.session_state["df_estructuras"] = df

        st.success("✅ Estructuras guardadas correctamente")

        return df, ruta

    return None, None
