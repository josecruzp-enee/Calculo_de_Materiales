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
# AGRUPAR CANTIDADES
# =========================================================
def _agrupar_cantidades(lista):

    conteo = {}

    for e in lista:
        conteo[e] = conteo.get(e, 0) + 1

    salida = []

    for est, cant in conteo.items():
        if cant > 1:
            salida.append(f"{cant}x{est}")
        else:
            salida.append(est)

    return ", ".join(sorted(salida))


# =========================================================
# CLASIFICACIÓN
# =========================================================
def _clasificar_en_fila(punto, df_punto):

    fila = {
        "Punto": punto,
        "Poste": [],
        "Primario": [],
        "Secundario": [],
        "Retenidas": [],
        "Conexiones a tierra": [],
        "Transformadores": [],
        "Luminarias": [],
    }

    for _, row in df_punto.iterrows():

        est = row["Estructuras"]

        if est.startswith("PC"):
            fila["Poste"].append(est)
        elif est.startswith("A-"):
            fila["Primario"].append(est)
        elif est.startswith("B-"):
            fila["Secundario"].append(est)
        elif est.startswith("R-"):
            fila["Retenidas"].append(est)
        elif est.startswith(("CA", "CS", "CT")):
            fila["Conexiones a tierra"].append(est)
        elif est.startswith("TS"):
            fila["Transformadores"].append(est)
        elif est.startswith("LL"):
            fila["Luminarias"].append(est)

    # convertir a texto con cantidades
    for k in fila:
        if k != "Punto":
            fila[k] = _agrupar_cantidades(fila[k])

    return fila


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
    # FORM
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

            c1, c2 = st.columns([6, 2])

            with c1:
                sel = st.selectbox(
                    cat,
                    valores if valores else [""],
                    key=f"{kp}_{cat}",
                    format_func=lambda x: f"{x} - {etiquetas.get(x, '')}"
                )

            with c2:
                qty = st.number_input(
                    "Cant",
                    min_value=1,
                    max_value=99,
                    value=1,
                    key=f"{kp}_{cat}_qty",
                    label_visibility="collapsed"
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
    # TABLA DEL PUNTO
    # =====================================================
    df_hist = st.session_state.get("df_puntos", pd.DataFrame())
    df_punto = df_hist[df_hist["Punto"] == punto]

    if not df_punto.empty:

        fila = _clasificar_en_fila(punto, df_punto)
        df_horizontal = pd.DataFrame([fila])

        st.markdown("### 📊 Vista del punto")
        st.dataframe(df_horizontal, use_container_width=True, hide_index=True)

    # =====================================================
    # TABLA GLOBAL
    # =====================================================
    if not df_hist.empty:

        filas = []

        for p in df_hist["Punto"].unique():
            df_p = df_hist[df_hist["Punto"] == p]
            filas.append(_clasificar_en_fila(p, df_p))

        df_all = pd.DataFrame(filas)

        st.markdown("### 📋 Tabla general del proyecto")
        st.dataframe(df_all, use_container_width=True, hide_index=True)

    # =====================================================
    # SALIDA FINAL
    # =====================================================
    df_final, ruta = construir_dataframe_salida()

    if df_final is not None and not df_final.empty:
        st.session_state["df_estructuras"] = df_final

    return df_final, ruta
