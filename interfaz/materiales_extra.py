# interfaz/materiales_ui.py
# SOLO UI — SIN LÓGICA DE NEGOCIO

from __future__ import annotations
import streamlit as st
import pandas as pd

from infraestructura.catalogo_materiales import obtener_catalogo_materiales
from dominio.entradas.materiales import (
    inicializar_materiales_extra,
    agregar_material,
    consolidar_materiales,
    limpiar_materiales,
)


def seccion_adicionar_material():

    st.subheader("4. 🧰 Adicionar Material")
    st.markdown("Agrega materiales adicionales al proyecto.")

    # Inicializar estado
    inicializar_materiales_extra()

    # Obtener catálogo (infraestructura)
    catalogo_df = obtener_catalogo_materiales()

    if catalogo_df is None or catalogo_df.empty:
        st.error("❌ No se pudo cargar el catálogo de materiales.")
        return

    # =====================================================
    # FORMULARIO
    # =====================================================
    with st.form("form_materiales"):

        col1, col2 = st.columns([4, 1])

        with col1:
            etiqueta_sel = st.selectbox(
                "🔧 Material",
                options=[""] + catalogo_df["Etiqueta"].tolist(),
                index=0
            )

        with col2:
            cantidad = st.number_input(
                "Cantidad",
                min_value=1,
                step=1,
                value=1
            )

        agregar = st.form_submit_button("➕ Agregar", use_container_width=True)

    # =====================================================
    # AGREGAR
    # =====================================================
    if agregar and etiqueta_sel:
        agregar_material(etiqueta_sel, cantidad)
        st.success("✅ Material agregado")

    # =====================================================
    # TABLA
    # =====================================================
    lista = st.session_state["materiales_extra"]

    if not lista:
        st.info("No hay materiales agregados.")
        return

    df_view = pd.DataFrame(lista).copy()
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
                "Unidad": st.column_config.TextColumn(disabled=True),
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

        st.session_state["materiales_extra"] = consolidar_materiales(
            edited.to_dict(orient="records")
        )

        st.success("✅ Cambios guardados")
        st.rerun()
