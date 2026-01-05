# -*- coding: utf-8 -*-
import re
import unicodedata

import streamlit as st
import pandas as pd
from modulo.entradas import cargar_catalogo_materiales


# ==========================================================
# Normalización de columnas del catálogo
# ==========================================================
def _sin_acentos(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", str(s))
        if unicodedata.category(c) != "Mn"
    )

def _norm_col(col: str) -> str:
    s = _sin_acentos(str(col)).lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _inferir_col_descripcion(df_original: pd.DataFrame) -> str | None:
    """
    Heurística por si el catálogo viene con encabezados raros.
    1) Busca columnas cuyo nombre contenga 'descripcion' o 'material'
    2) Si no hay, escoge la columna de texto más 'larga' (promedio de longitud)
       excluyendo columnas típicas de código/unidad/referencia.
    """
    if df_original is None or df_original.empty:
        return None

    # 1) Por nombre
    candidatas = []
    for c in df_original.columns:
        cn = _norm_col(c)
        if ("descripcion" in cn) or ("material" in cn):
            score = 0
            if "descripcion" in cn:
                score += 3
            if "material" in cn:
                score += 2
            candidatas.append((score, c))

    if candidatas:
        candidatas.sort(reverse=True, key=lambda x: x[0])
        return candidatas[0][1]

    # 2) Por contenido (columna de texto con strings más largos)
    excluir = {
        "n", "no", "n°", "nº",
        "codigo", "código",
        "unidad", "und", "u",
        "referencia", "ref"
    }

    mejores = []
    for c in df_original.columns:
        cn = _norm_col(c)
        if cn in excluir or any(cn.startswith(e) for e in excluir):
            continue

        ser = df_original[c].astype(str).fillna("").str.strip()
        # si casi todo está vacío, no sirve
        if (ser == "").mean() > 0.8:
            continue

        score = ser.map(len).mean()  # promedio de longitud
        mejores.append((score, c))

    if not mejores:
        return None

    mejores.sort(reverse=True, key=lambda x: x[0])
    return mejores[0][1]


def normalizar_columnas_catalogo(catalogo_df: pd.DataFrame) -> pd.DataFrame:
    """
    Renombra columnas del catálogo para que existan siempre:
      - Descripcion
      - Unidad

    Soporta encabezados como:
      'DESCRIPCIÓN DE MATERIALES', 'DESCRIPCION', 'DESCRIPCIÓN', etc.
    """
    if catalogo_df is None or catalogo_df.empty:
        return pd.DataFrame(columns=["Descripcion", "Unidad"])

    df_original = catalogo_df.copy()
    df = catalogo_df.copy()

    rename = {}
    for c in df.columns:
        cn = _norm_col(c)

        # Descripción (incluye "DESCRIPCIÓN DE MATERIALES")
        if "descripcion" in cn:
            rename[c] = "Descripcion"

        # Unidad
        elif cn.startswith("unidad") or cn in ("und", "u"):
            rename[c] = "Unidad"

    df = df.rename(columns=rename)

    # Asegurar columnas
    if "Descripcion" not in df.columns:
        df["Descripcion"] = ""
    if "Unidad" not in df.columns:
        df["Unidad"] = ""

    # Limpieza ligera
    df["Descripcion"] = df["Descripcion"].astype(str).fillna("").str.strip()
    df["Unidad"] = df["Unidad"].astype(str).fillna("").str.strip()

    # ✅ Fallback: si Descripcion quedó vacía, intentar inferir desde df_original
    if (df["Descripcion"] == "").all():
        col_desc = _inferir_col_descripcion(df_original)
        if col_desc is not None:
            df["Descripcion"] = df_original[col_desc].astype(str).fillna("").str.strip()

    return df


# ==========================================================
# Consolidación de materiales extra
# ==========================================================
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


# ==========================================================
# UI Streamlit
# ==========================================================
def seccion_adicionar_material():
    st.subheader("4. 🧰 Adicionar Material")
    st.markdown("Agrega materiales adicionales al proyecto que no estén asociados a estructuras específicas.")

    # Estado
    if "materiales_extra" not in st.session_state:
        st.session_state["materiales_extra"] = []

    # Catálogo (para el selector)
    ruta = st.session_state.get("ruta_datos_materiales", None)
    catalogo_raw = cargar_catalogo_materiales(ruta)

    if catalogo_raw is None or catalogo_raw.empty:
        st.warning("⚠️ No se pudo cargar el catálogo de materiales.")
        return

    # ✅ Normalizar encabezados (evita KeyError y detecta 'DESCRIPCIÓN DE MATERIALES')
    catalogo_df = normalizar_columnas_catalogo(catalogo_raw)

    # ✅ Si aún está vacío, mejor avisar y mostrar columnas para debug rápido
    if (catalogo_df.get("Descripcion", "") == "").all():
        st.error("❌ No se logró detectar la columna de descripción del catálogo.")
        st.write("Columnas detectadas en el Excel:", list(catalogo_raw.columns))
        st.stop()

    # ✅ IMPORTANTÍSIMO: filtra filas sin descripción para que no salga “– C/U”
    catalogo_df["Descripcion"] = catalogo_df["Descripcion"].astype(str).fillna("").str.strip()
    catalogo_df["Unidad"] = catalogo_df["Unidad"].astype(str).fillna("").str.strip()
    catalogo_df = catalogo_df[catalogo_df["Descripcion"] != ""].copy()

    # Armar etiqueta (vectorizado, rápido)
    # Si Unidad está vacía, la etiqueta queda solo con descripción.
    desc = catalogo_df["Descripcion"]
    unit = catalogo_df["Unidad"]
    catalogo_df["Etiqueta"] = desc.where(unit == "", desc + " – " + unit)

    # Quitar duplicadas y ordenar
    catalogo_df = catalogo_df.drop_duplicates(subset=["Etiqueta"]).sort_values("Etiqueta")
    opciones_materiales = [""] + catalogo_df["Etiqueta"].tolist()

    # --- Form para agregar ---
    with st.form("form_adicionar_material", clear_on_submit=False):
        col1, col2 = st.columns([4, 1])
        with col1:
            etiqueta_sel = st.selectbox(
                "🔧 Selecciona el Material",
                options=opciones_materiales,
                index=0,
                placeholder="Ejemplo: Abrazadera Doble Ajustable... – C/U",
                key="sel_material_extra"
            )
        with col2:
            cantidad = st.number_input(
                "🔢 Cantidad", min_value=1, step=1, value=1, key="num_cantidad_extra"
            )

        agregar = st.form_submit_button("➕ Agregar Material", use_container_width=True)

    if agregar and etiqueta_sel:
        # Parse etiqueta -> material + unidad
        partes = etiqueta_sel.split(" – ", 1)
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
                "Cantidad": st.column_config.NumberColumn("Cantidad", min_value=0, step=1, help="Puedes ajustar aquí"),
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

        # 2) cantidades
        if "Cantidad" in edited.columns:
            edited["Cantidad"] = pd.to_numeric(edited["Cantidad"], errors="coerce").fillna(0).astype(int)
            edited = edited[edited["Cantidad"] > 0]

        # 3) consolidar
        st.session_state["materiales_extra"] = _consolidar_materiales(edited.to_dict(orient="records"))
        st.success("✅ Cambios aplicados correctamente.")
        st.rerun()
