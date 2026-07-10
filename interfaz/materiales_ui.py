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

    # =====================================================
    # CARGAR CATÁLOGO
    # =====================================================
    from entradas.base_datos import cargar_base_datos

    base = cargar_base_datos()

    catalogo_df = pd.DataFrame(
        columns=["Materiales", "Unidad"]
    )

    # La base normalmente viene como dict de hojas
    if isinstance(base, dict):

        posibles_hojas = [
            "MATERIALES",
            "CATALOGO",
            "CATÁLOGO",
            "PRECIOS",
        ]

        for nombre_hoja in posibles_hojas:

            df_hoja = base.get(nombre_hoja)

            if isinstance(df_hoja, pd.DataFrame) and not df_hoja.empty:
                catalogo_df = df_hoja.copy()
                break

    elif isinstance(base, pd.DataFrame):
        catalogo_df = base.copy()

    # =====================================================
    # DETECTAR COLUMNAS DEL CATÁLOGO
    # =====================================================
    columna_material = None
    columna_unidad = None

    for columna in catalogo_df.columns:

        nombre = str(columna).strip().lower()

        if columna_material is None and (
            "material" in nombre
            or "descripcion" in nombre
            or "descripción" in nombre
            or "etiqueta" in nombre
        ):
            columna_material = columna

        if columna_unidad is None and (
            nombre == "unidad"
            or "unidad" in nombre
        ):
            columna_unidad = columna

    opciones_materiales = []

    if columna_material is not None:

        opciones_materiales = (
            catalogo_df[columna_material]
            .dropna()
            .astype(str)
            .str.strip()
        )

        opciones_materiales = [
            material
            for material in opciones_materiales.unique().tolist()
            if material
        ]

        opciones_materiales = sorted(opciones_materiales)

    # =====================================================
    # FORMULARIO
    # =====================================================
    with st.form("form_materiales"):

        col1, col2 = st.columns([4, 1])

        with col1:

            if opciones_materiales:

                etiqueta_sel = st.selectbox(
                    "🔧 Material",
                    options=opciones_materiales,
                    index=None,
                    placeholder="Seleccione un material",
                )

            else:

                st.warning(
                    "No se encontró un catálogo de materiales. "
                    "Puede escribir el material manualmente."
                )

                etiqueta_sel = st.text_input(
                    "🔧 Material",
                    placeholder="Escriba el material",
                )

        with col2:
            cantidad = st.number_input(
                "Cantidad",
                min_value=1.0,
                value=1.0,
                step=1.0,
            )

        agregar = st.form_submit_button(
            "➕ Agregar",
            use_container_width=True,
        )

    # =====================================================
    # OBTENER UNIDAD AUTOMÁTICA
    # =====================================================
    unidad_sel = ""

    if (
        etiqueta_sel
        and columna_material is not None
        and columna_unidad is not None
        and not catalogo_df.empty
    ):

        coincidencia = catalogo_df[
            catalogo_df[columna_material]
            .astype(str)
            .str.strip()
            .eq(str(etiqueta_sel).strip())
        ]

        if not coincidencia.empty:
            unidad_sel = str(
                coincidencia.iloc[0][columna_unidad]
            ).strip()

    # =====================================================
    # AGREGAR
    # =====================================================
    if agregar and etiqueta_sel:

        agregar_material(
            etiqueta_sel,
            unidad_sel,
            cantidad,
        )

        st.success("✅ Material agregado")
        st.rerun()

    # =====================================================
    # TABLA
    # =====================================================
    df_actual = st.session_state.get(
        "materiales_extra",
        pd.DataFrame(),
    )

    if df_actual is None or df_actual.empty:
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
                "__DEL__": st.column_config.CheckboxColumn(
                    "Eliminar"
                ),
                "Materiales": st.column_config.TextColumn(
                    "Material",
                    disabled=True,
                ),
                "Unidad": st.column_config.TextColumn(
                    "Unidad"
                ),
                "Cantidad": st.column_config.NumberColumn(
                    "Cantidad",
                    min_value=0,
                ),
            },
        )

        c1, c2 = st.columns(2)

        guardar = c1.form_submit_button(
            "💾 Guardar",
            type="primary",
        )

        limpiar = c2.form_submit_button(
            "🗑️ Limpiar",
        )

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
            edited = edited.loc[
                ~edited["__DEL__"].fillna(False)
            ]

        edited = edited.drop(
            columns="__DEL__",
            errors="ignore",
        )

        df_final = consolidar_materiales(edited)

        st.session_state["materiales_extra"] = df_final

        st.success("✅ Cambios guardados")
        st.rerun()
