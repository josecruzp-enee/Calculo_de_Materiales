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

from entradas.base_datos import cargar_base_datos


# =========================================================
# CATÁLOGO
# =========================================================
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
        elif c.startswith(("CA", "CS", "CT")): return "Conexiones a tierra"
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

    st.divider()

    # =====================================================
    # FORM (🔥 CLAVE PARA EVITAR RERUN MOLESTO)
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

    with st.form(key=f"form_{punto}"):

        seleccion_temp = []

        for cat in categorias:

            valores = opciones.get(cat, {}).get("valores", [])
            etiquetas = opciones.get(cat, {}).get("etiquetas", {})

            sel = st.selectbox(
                cat,
                valores if valores else [""],
                key=f"{kp}_{cat}",
                format_func=lambda x: f"{x} - {etiquetas.get(x, '')}"
            )

            qty = st.number_input(
                f"Cantidad {cat}",
                min_value=1,
                max_value=99,
                value=1,
                key=f"{kp}_{cat}_qty"
            )

            if sel:
                for _ in range(qty):
                    seleccion_temp.append(sel)

        guardar_punto = st.form_submit_button("💾 Guardar punto")

        if guardar_punto:

            for est in seleccion_temp:
                agregar_item_estructura(punto, est)

            st.success(f"✅ {punto} guardado correctamente")

    # =====================================================
    # VISUALIZACIÓN
    # =====================================================
    df_hist = st.session_state.get("df_puntos", pd.DataFrame())
    df_punto = df_hist[df_hist["Punto"] == punto]

    if not df_punto.empty:
        st.markdown("### 📌 Estructuras en este punto")
        st.dataframe(df_punto, use_container_width=True, hide_index=True)
    else:
        st.info("Este punto aún no tiene estructuras")

    # =====================================================
    # RESUMEN
    # =====================================================
    fila_actual = consolidar_punto(punto)

    if fila_actual and fila_actual.get("Estructuras"):
        st.markdown("### 🧾 Resumen del punto")

        df_sel = pd.DataFrame({
            "Estructura": fila_actual["Estructuras"]
        })

        st.dataframe(df_sel, use_container_width=True, hide_index=True)

    # =====================================================
    # HISTÓRICO
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
    # SALIDA FINAL
    # =====================================================
    df_final, ruta = construir_dataframe_salida()

    if df_final is not None and not df_final.empty:
        st.session_state["df_estructuras"] = df_final

    return df_final, ruta
