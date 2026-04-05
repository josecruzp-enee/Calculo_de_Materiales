# -*- coding: utf-8 -*-
# interfaz/materiales_ui.py

from __future__ import annotations
import streamlit as st
import pandas as pd

from interfaz.materiales_extra import (
    inicializar_materiales_extra,
    agregar_material,
    consolidar_materiales,
    limpiar_materiales,
    obtener_materiales_finales,
)


def seccion_adicionar_material():

    st.subheader("4. 🧰 Adicionar Material")
    st.markdown("Agrega materiales adicionales al proyecto.")

    inicializar_materiales_extra()

    # ⚠️ Este catálogo debe venir de otro módulo (NO entradas)
    from entradas.base_datos import cargar_base_datos

    base = cargar_base_datos()

    # fallback simple
    catalogo_df = pd.DataFrame({
        "Etiqueta": []
    })

    # =====================================================
    # FORMULARIO
    # =====================================================
    with st.form("form_materiales"):

        col1, col2 = st.columns([4, 1])

        with col1:
            etiqueta_sel = st.text_input("🔧 Material")

        with col2:
            cantidad = st.number_input("Cantidad", min_value=1, value=1)

        agregar = st.form_submit_button("➕ Agregar", use_container_width=True)

    if agregar and etiqueta_sel:
        agregar_material(etiqueta_sel, "", cantidad)
        st.success("✅ Material agregado")

    # =====================================================
    # TABLA
    # =====================================================
    df_actual = st.session_state.get("materiales_extra", pd.DataFrame())

    if df_actual.empty:
        st.info("No hay materiales agregados.")
        return

    df_view = df_actual.copy()
    df_view.insert(0, "__DEL__", False)

    st.markdown("### 📋 Materiales")

    with st.form("form_tabla"):

        edited = st.data_editor(
            df_view,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "__DEL__": st.column_config.CheckboxColumn("Eliminar"),
                "Materiales": st.column_config.TextColumn(disabled=True),
                "Unidad": st.column_config.TextColumn(),
                "Cantidad": st.column_config.NumberColumn(min_value=0),
            },
        )

        c1, c2 = st.columns(2)

        guardar = c1.form_submit_button("💾 Guardar", type="primary")
        limpiar = c2.form_submit_button("🗑️ Limpiar")

    # =====================================================
    # LIMPIAR
    # =====================================================
    if limpiar:
        limpiar_materiales()
        st.rerun()

    # =====================================================
    # GUARDAR
    # =====================================================
    if guardar:

        if "__DEL__" in edited.columns:
            edited = edited.loc[~edited["__DEL__"]]

        df_final = consolidar_materiales(edited.drop(columns="__DEL__"))

        st.session_state["materiales_extra"] = df_final

        st.success("✅ Cambios guardados")
        st.rerun()
