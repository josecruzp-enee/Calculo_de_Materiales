# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from modulo.entradas import cargar_catalogo_materiales


def _consolidar_materiales(lista):
    """Une duplicados por (Materiales, Unidad) sumando cantidades."""
    if not lista:
        return []
    df = pd.DataFrame(lista)
    if df.empty:
        return []
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0).astype(int)
    df = (
        df.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
          .sort_values(["Materiales", "Unidad"])
    )
    return df.to_dict(orient="records")


def seccion_adicionar_material():
    st.subheader("4. 🧰 Adicionar Material")
    st.markdown("Agrega materiales adicionales al proyecto que no estén asociados a estructuras específicas.")

    # Estado
    if "materiales_extra" not in st.session_state:
        st.session_state["materiales_extra"] = []

    # Catálogo
    ruta = st.session_state.get("ruta_datos_materiales", None)
    catalogo_df = cargar_catalogo_materiales(ruta)

    # 🔎 DEBUG (útil si vuelve a salir solo “– C/U”)
    with st.expander("🧪 DEBUG catálogo", expanded=False):
        st.write("Ruta:", ruta)
        st.write("Columnas:", list(catalogo_df.columns) if catalogo_df is not None else None)
        if catalogo_df is not None:
            st.dataframe(catalogo_df.head(30), use_container_width=True)

    if catalogo_df is None or catalogo_df.empty:
        st.warning("⚠️ No se pudo cargar el catálogo de materiales (o viene vacío).")
        return

    # Si Descripcion viene vacía, entonces el Excel se está leyendo mal
    if (catalogo_df["Descripcion"].astype(str).str.strip() == "").all():
        st.error("❌ La columna 'Descripcion' viene vacía. Revisa el DEBUG catálogo (arriba).")
        return

    # Etiqueta para el selector
    catalogo_df = catalogo_df.copy()

    # filtro: elimina filas sin descripción (evita “– C/U”)
    catalogo_df = catalogo_df[catalogo_df["Descripcion"].astype(str).str.strip() != ""].copy()

    catalogo_df["Etiqueta"] = catalogo_df.apply(
        lambda x: f"{x.get('Descripcion','')} – {x.get('Unidad','')}".strip().rstrip(" –"),
        axis=1
    )

    opciones_materiales = [""] + catalogo_df["Etiqueta"].tolist()

    # --- Form para agregar ---
    with st.form("form_adicionar_material", clear_on_submit=False):
        col1, col2 = st.columns([4, 1])

        with col1:
            etiqueta_sel = st.selectbox(
                "🔧 Selecciona el Material",
                options=opciones_materiales,
                index=0,
                placeholder="Ejemplo: Abrazadera ... – C/U",
                key="sel_material_extra"
            )

        with col2:
            cantidad = st.number_input(
                "🔢 Cantidad", min_value=1, step=1, value=1, key="num_cantidad_extra"
            )

        agregar = st.form_submit_button("➕ Agregar Material", use_container_width=True)

    if agregar and etiqueta_sel:
        partes = etiqueta_sel.split(" – ")
        material = partes[0].strip()
        unidad = partes[1].strip() if len(partes) > 1 else ""

        st.session_state["materiales_extra"].append({
            "Materiales": material,
            "Unidad": unidad,
            "Cantidad": int(cantidad)
        })

        st.session_state["materiales_extra"] = _consolidar_materiales(st.session_state["materiales_extra"])
        st.success(f"✅ Material agregado: {material} ({cantidad} {unidad})")

    # --- Tabla editable con Eliminar ---
    lista = st.session_state["materiales_extra"]
    if not lista:
        st.info("Aún no has agregado materiales adicionales.")
        return

    df_view = pd.DataFrame(lista).copy()
    df_view.insert(0, "__DEL__", False)

    st.markdown("### 📋 Materiales adicionales añadidos")
    with st.form("form_editar_eliminar_materiales", clear_on_submit=False):
        edited = st.data_editor(
            df_view,
            key="editor_materiales_adicionales",
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "__DEL__": st.column_config.CheckboxColumn("Eliminar", help="Marca y pulsa 'Guardar cambios'"),
                "Materiales": st.column_config.TextColumn("Materiales", disabled=True),
                "Unidad": st.column_config.TextColumn("Unidad", disabled=True),
                "Cantidad": st.column_config.NumberColumn("Cantidad", min_value=0, step=1),
            },
        )

        c1, c2, _ = st.columns([1, 1, 2])
        guardar = c1.form_submit_button("💾 Guardar cambios", type="primary", use_container_width=True)
        limpiar = c2.form_submit_button("🗑️ Limpiar todo", use_container_width=True)

    if limpiar:
        st.session_state["materiales_extra"] = []
        st.info("Se limpiaron todos los materiales adicionales.")
        st.rerun()

    if guardar:
        # 1) eliminaciones
        if "__DEL__" in edited.columns:
            edited = edited.loc[~edited["__DEL__"].fillna(False)].drop(columns="__DEL__", errors="ignore")

        # 2) normalizar cantidades (>0)
        if "Cantidad" in edited.columns:
            edited["Cantidad"] = pd.to_numeric(edited["Cantidad"], errors="coerce").fillna(0).astype(int)
            edited = edited[edited["Cantidad"] > 0]

        # 3) consolidar
        st.session_state["materiales_extra"] = _consolidar_materiales(edited.to_dict(orient="records"))

        st.success("✅ Cambios aplicados correctamente.")
        st.rerun()
