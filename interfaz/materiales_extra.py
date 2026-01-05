# interfaz/materiales_extra.py
# -*- coding: utf-8 -*-
import re
import unicodedata
import streamlit as st
import pandas as pd
from modulo.entradas import cargar_catalogo_materiales


def _sin_acentos(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", str(s))
        if unicodedata.category(c) != "Mn"
    )

def _norm_col(col: str) -> str:
    s = _sin_acentos(str(col)).lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s

def normalizar_columnas_catalogo(catalogo_df: pd.DataFrame) -> pd.DataFrame:
    """
    Renombra columnas del catálogo para que existan siempre:
      - Descripcion
      - Unidad
    Soporta: 'DESCRIPCIÓN DE MATERIALES', 'DESCRIPCION', etc.
    """
    if catalogo_df is None or catalogo_df.empty:
        return pd.DataFrame(columns=["Descripcion", "Unidad"])

    df = catalogo_df.copy()
    rename = {}

    for c in df.columns:
        cn = _norm_col(c)

        # detecta descripción
        if "descripcion" in cn:
            rename[c] = "Descripcion"

        # detecta unidad
        if cn == "unidad" or cn.startswith("unidad") or cn in ("und", "u"):
            rename[c] = "Unidad"

    df = df.rename(columns=rename)

    # asegurar columnas aunque vengan mal
    if "Descripcion" not in df.columns:
        df["Descripcion"] = ""
    if "Unidad" not in df.columns:
        df["Unidad"] = ""

    df["Descripcion"] = df["Descripcion"].astype(str).fillna("").str.strip()
    df["Unidad"] = df["Unidad"].astype(str).fillna("").str.strip()

    return df


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

    # cargar catálogo
    catalogo_df = cargar_catalogo_materiales(st.session_state.get("ruta_datos_materiales", None))
    if catalogo_df is None or catalogo_df.empty:
        st.warning("⚠️ No se pudo cargar el catálogo de materiales.")
        return

    # DEBUG útil (puedes borrarlo cuando funcione)
    st.caption(f"Columnas detectadas: {list(catalogo_df.columns)}")

    # normalizar columnas
    catalogo_df = normalizar_columnas_catalogo(catalogo_df)

    # si descripcion viene vacía, el problema está en cargar_catalogo_materiales
    if (catalogo_df["Descripcion"].astype(str).str.strip() == "").all():
        st.error("❌ No se logró detectar la columna de descripción del catálogo.")
        st.write("Columnas detectadas en el Excel:", list(catalogo_df.columns))
        return

    catalogo_df["Etiqueta"] = catalogo_df.apply(
        lambda x: f"{x.get('Descripcion','')} – {x.get('Unidad','')}".strip().rstrip(" –"),
        axis=1
    )

    opciones_materiales = [""] + catalogo_df["Etiqueta"].tolist()

    with st.form("form_adicionar_material", clear_on_submit=False):
        col1, col2 = st.columns([4, 1])
        with col1:
            etiqueta_sel = st.selectbox(
                "🔧 Selecciona el Material",
                options=opciones_materiales,
                index=0,
                placeholder="Ejemplo: Abrazadera... – C/U",
                key="sel_material_extra"
            )
        with col2:
            cantidad = st.number_input("🔢 Cantidad", min_value=1, step=1, value=1, key="num_cantidad_extra")

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
                "__DEL__": st.column_config.CheckboxColumn("Eliminar"),
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
