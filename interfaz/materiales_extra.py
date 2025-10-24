# -*- coding: utf-8 -*-
# interfaz/materiales_extra.py

import pandas as pd
import streamlit as st
from interfaz.base import ruta_datos_materiales_por_defecto
from modulo.entradas import cargar_catalogo_materiales

def seccion_adicionar_material() -> None:
    st.subheader("4. 🧰 Adicionar Material")
    st.markdown("Agrega materiales adicionales al proyecto que no estén asociados a estructuras específicas.")

    if "materiales_extra" not in st.session_state:
        st.session_state["materiales_extra"] = []

    catalogo_df = cargar_catalogo_materiales(ruta_datos_materiales_por_defecto())
    if catalogo_df.empty:
        st.warning("⚠️ No se pudo cargar el catálogo de materiales.")
        return

    catalogo_df["Etiqueta"] = catalogo_df.apply(
        lambda x: f"{x['Descripcion']} – {x['Unidad']}" if pd.notna(x["Unidad"]) else x["Descripcion"],
        axis=1
    )
    opciones_materiales = catalogo_df["Etiqueta"].tolist()

    with st.form("form_adicionar_material"):
        col1, col2 = st.columns([3, 1])
        with col1:
            etiqueta_sel = st.selectbox(
                "🔧 Selecciona el Material",
                options=[""] + opciones_materiales,
                index=0,
                placeholder="Ejemplo: BOMBILLO PARA LÁMPARA – C/U",
                key="sel_material_extra"
            )
        with col2:
            cantidad = st.number_input("🔢 Cantidad", min_value=1, step=1, value=1, key="num_cantidad_extra")

        agregar = st.form_submit_button("➕ Agregar Material")

    if agregar and etiqueta_sel:
        agregar_material_extra(etiqueta_sel, cantidad)

    if st.session_state["materiales_extra"]:
        st.markdown("### 📋 Materiales adicionales añadidos")
        st.dataframe(pd.DataFrame(st.session_state["materiales_extra"]), use_container_width=True, hide_index=True)

def agregar_material_extra(etiqueta_sel: str, cantidad: int) -> None:
    """Agrega un material adicional a session_state a partir de la etiqueta seleccionada."""
    partes = etiqueta_sel.split(" – ")
    material = partes[0].strip()
    unidad = partes[1].strip() if len(partes) > 1 else ""
    st.session_state["materiales_extra"].append({
        "Materiales": material,
        "Unidad": unidad,
        "Cantidad": int(cantidad)
    })
    st.success(f"✅ Material agregado: {material} ({cantidad} {unidad})")
