# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from entradas.excel_legacy import cargar_catalogo_materiales

def _consolidar_materiales(lista):
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

    if "materiales_extra" not in st.session_state:
        st.session_state["materiales_extra"] = []

    ruta = st.session_state.get("ruta_datos_materiales", None)
    catalogo_df = cargar_catalogo_materiales(ruta)

    if catalogo_df is None or catalogo_df.empty:
        st.error("❌ No se pudo cargar el catálogo de materiales (hoja Materiales).")
        st.write("Ruta detectada:", ruta)
        return

    # ✅ este check es el que te está disparando el mensaje ahora:
    # no es que falte la columna, es que viene VACÍA.
    if (catalogo_df["Descripcion"].astype(str).str.strip() == "").all():
        st.error("❌ El catálogo cargó, pero la columna de descripción viene vacía.")
        st.write("Columnas encontradas en el catálogo:", catalogo_df.columns.tolist())
        st.write("Primeras filas:")
        st.dataframe(catalogo_df.head(10), use_container_width=True)
        st.info("👉 Esto significa que el Excel se está leyendo mal (header/usecols/skiprows). Con la nueva función cargar_catalogo_materiales debería corregirse.")
        return

    # Etiqueta más robusta: incluye código
    catalogo_df["Etiqueta"] = catalogo_df.apply(
        lambda x: f"{x.get('Codigo','').strip()} | {x.get('Descripcion','').strip()} – {x.get('Unidad','').strip()}".strip().rstrip(" –"),
        axis=1
    )

    # Opciones (filtra vacías)
    opciones_materiales = [""] + catalogo_df["Etiqueta"].dropna().astype(str).tolist()

    with st.form("form_adicionar_material", clear_on_submit=False):
        col1, col2 = st.columns([4, 1])
        with col1:
            etiqueta_sel = st.selectbox(
                "🔧 Selecciona el Material",
                options=opciones_materiales,
                index=0,
                placeholder="Ejemplo: AB1 | Abrazadera... – C/U",
                key="sel_material_extra"
            )
        with col2:
            cantidad = st.number_input("🔢 Cantidad", min_value=1, step=1, value=1, key="num_cantidad_extra")

        agregar = st.form_submit_button("➕ Agregar Material", use_container_width=True)

    if agregar and etiqueta_sel:
        # "AB1 | Abrazadera... – C/U"
        partes = etiqueta_sel.split(" – ")
        izq = partes[0].strip()
        unidad = partes[1].strip() if len(partes) > 1 else ""

        # izq = "AB1 | Abrazadera..."
        if " | " in izq:
            _, material = izq.split(" | ", 1)
        else:
            material = izq

        material = material.strip()

        st.session_state["materiales_extra"].append({
            "Materiales": material,
            "Unidad": unidad,
            "Cantidad": int(cantidad)
        })
        st.session_state["materiales_extra"] = _consolidar_materiales(st.session_state["materiales_extra"])
        st.success(f"✅ Material agregado: {material} ({cantidad} {unidad})")

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
        c1, c2 = st.columns([1, 1])
        guardar = c1.form_submit_button("💾 Guardar cambios", type="primary", use_container_width=True)
        limpiar = c2.form_submit_button("🗑️ Limpiar todo", use_container_width=True)

    if limpiar:
        st.session_state["materiales_extra"] = []
        st.info("Se limpiaron todos los materiales adicionales.")
        st.rerun()

    if guardar:
        if "__DEL__" in edited.columns:
            edited = edited.loc[~edited["__DEL__"].fillna(False)].drop(columns="__DEL__", errors="ignore")

        edited["Cantidad"] = pd.to_numeric(edited["Cantidad"], errors="coerce").fillna(0).astype(int)
        edited = edited[edited["Cantidad"] > 0]

        st.session_state["materiales_extra"] = _consolidar_materiales(edited.to_dict(orient="records"))
        st.success("✅ Cambios aplicados correctamente.")
        st.rerun()
