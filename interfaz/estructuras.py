# -*- coding: utf-8 -*-
# interfaz/estructuras.py

from __future__ import annotations
import pandas as pd
import streamlit as st

from interfaz.base import COLUMNAS_BASE, resetear_desplegables
from modulo.utils import guardar_archivo_temporal, pegar_texto_a_df
from modulo.entradas import cargar_estructuras_proyectadas


# ==============================
# Modo: cargar desde Excel
# ==============================
def cargar_desde_excel():
    archivo_estructuras = st.file_uploader("Archivo de estructuras", type=["xlsx"], key="upl_estructuras")
    if archivo_estructuras:
        ruta_estructuras = guardar_archivo_temporal(archivo_estructuras)
        try:
            df = cargar_estructuras_proyectadas(ruta_estructuras)
            st.success("✅ Hoja 'estructuras' leída correctamente")
            return df, ruta_estructuras
        except Exception as e:
            st.error(f"❌ No se pudo leer la hoja 'estructuras': {e}")
    return pd.DataFrame(columns=COLUMNAS_BASE), None


# ==============================
# Modo: pegar tabla
# ==============================
def pegar_tabla():
    texto_pegado = st.text_area("Pega aquí tu tabla CSV/tabulado", height=200, key="txt_pegar_tabla")
    if texto_pegado:
        df = pegar_texto_a_df(texto_pegado, COLUMNAS_BASE)
        st.success(f"✅ Tabla cargada con {len(df)} filas")
        return df
    return pd.DataFrame(columns=COLUMNAS_BASE)


# =========================================================
# NUEVO MODO: Listas con Select + Cantidad + Agregar (PRO)
# =========================================================

# ---- Estado por punto (diccionario consolidado) ----
def _init_punto_state():
    if "df_puntos" not in st.session_state:
        st.session_state["df_puntos"] = pd.DataFrame(columns=COLUMNAS_BASE)

    if "punto_en_edicion" not in st.session_state:
        df = st.session_state["df_puntos"]
        if not df.empty:
            st.session_state["punto_en_edicion"] = df["Punto"].iloc[0]
        else:
            st.session_state["punto_en_edicion"] = "Punto 1"

    if "puntos_data" not in st.session_state:
        st.session_state["puntos_data"] = {}

    p = st.session_state["punto_en_edicion"]
    if p not in st.session_state["puntos_data"]:
        st.session_state["puntos_data"][p] = {
            "Poste": {},
            "Primario": {},
            "Secundario": {},
            "Retenidas": {},
            "Conexiones a tierra": {},
            "Transformadores": {},
        }


def add_item(categoria: str, codigo: str, cantidad: int):
    """Consolida X + X => 2× X dentro del Punto actual."""
    if not codigo or cantidad <= 0:
        return
    p = st.session_state["punto_en_edicion"]
    bucket = st.session_state["puntos_data"][p][categoria]
    bucket[codigo] = bucket.get(codigo, 0) + int(cantidad)


def remove_item(categoria: str, codigo: str, all_qty: bool = False):
    """Resta 1 unidad o elimina por completo un código de la categoría."""
    p = st.session_state["punto_en_edicion"]
    bucket = st.session_state["puntos_data"][p][categoria]
    if codigo in bucket:
        if all_qty or bucket[codigo] <= 1:
            bucket.pop(codigo, None)
        else:
            bucket[codigo] -= 1


def render_cat_str(punto: str, categoria: str) -> str:
    """Convierte el dict consolidado en texto: '2× R-1, A-I-5'."""
    data = st.session_state["puntos_data"][punto][categoria]
    if not data:
        return ""
    parts = []
    for code, n in data.items():
        parts.append(f"{n}× {code}" if n > 1 else code)
    return ", ".join(parts)


# ---- Opciones (códigos + etiquetas) desde tu Excel/índice ----
def _opciones_categoria(opciones_dict, llave_catalogo: str) -> tuple[list[str], dict]:
    """
    opciones_dict viene de modulo.desplegables.cargar_opciones()
    Estructura típica:
      {
        "Poste": {"valores": [...], "etiquetas": {codigo: "codigo – desc", ...}},
        "Primario": {...}, "Secundario": {...}, "Retenidas": {...},
        "Conexiones a tierra": {...}, "Transformadores": {...}
      }
    """
    bloque = opciones_dict.get(llave_catalogo) or {}
    valores = bloque.get("valores", []) or []
    etiquetas = bloque.get("etiquetas", {}) or {}
    return valores, etiquetas


def _val_or_dash(s: str) -> str:
    """Muestra '-' cuando no hay selección (opción B)."""
    return s if (s and str(s).strip()) else "-"


def _consolidado_a_fila(punto: str) -> dict:
    """Devuelve una fila compatible con COLUMNAS_BASE a partir del dict consolidado."""
    return {
        "Punto": punto,
        "Poste": _val_or_dash(render_cat_str(punto, "Poste")),
        "Primario": _val_or_dash(render_cat_str(punto, "Primario")),
        "Secundario": _val_or_dash(render_cat_str(punto, "Secundario")),
        "Retenidas": _val_or_dash(render_cat_str(punto, "Retenidas")),
        "Conexiones a tierra": _val_or_dash(render_cat_str(punto, "Conexiones a tierra")),
        "Transformadores": _val_or_dash(render_cat_str(punto, "Transformadores")),
    }


def listas_desplegables():
    """
    UI de edición por Punto con UNA FILA HORIZONTAL:
    [Poste ▼][Primario ▼][Secundario ▼][Retenidas ▼][Tierra ▼][Trafo ▼][ 1 ][➕ Agregar todo]
    """
    from modulo.desplegables import cargar_opciones
    opciones = cargar_opciones()

    st.subheader("3. 🏗️ Estructuras del Proyecto")

    _init_punto_state()
    df_actual = st.session_state["df_puntos"]

    # ---------- Barra superior ----------
    colA, colB, colC, colD = st.columns([1.2, 1.2, 1.8, 1.2])
    with colA:
        if st.button("🆕 Crear nuevo Punto"):
            existentes = df_actual["Punto"].unique().tolist() if not df_actual.empty else []
            nums = [int("".join(filter(str.isdigit, p))) for p in existentes if any(c.isdigit() for c in p)]
            nuevo = f"Punto {(max(nums) + 1) if nums else 1}"

            st.session_state["punto_en_edicion"] = nuevo
            st.session_state["puntos_data"][nuevo] = {
                "Poste": {}, "Primario": {}, "Secundario": {},
                "Retenidas": {}, "Conexiones a tierra": {}, "Transformadores": {}
            }
            st.success(f"✏️ {nuevo} listo para editar")
            resetear_desplegables()

    with colB:
        if not df_actual.empty:
            p_sel = st.selectbox("📍 Ir a punto:", df_actual["Punto"].unique(), key="sel_goto_punto")
            if st.button("✏️ Editar", key="btn_editar_punto"):
                st.session_state["punto_en_edicion"] = p_sel
                resetear_desplegables()

    with colC:
        if not df_actual.empty:
            p_del = st.selectbox("❌ Borrar punto:", df_actual["Punto"].unique(), key="sel_del_punto")
            if st.button("Borrar", key="btn_borrar_punto"):
                st.session_state["df_puntos"] = df_actual[df_actual["Punto"] != p_del].reset_index(drop=True)
                st.session_state["puntos_data"].pop(p_del, None)
                st.success(f"✅ Se eliminó {p_del}")

    with colD:
        if st.button("🧹 Limpiar todo"):
            st.session_state["df_puntos"] = pd.DataFrame(columns=COLUMNAS_BASE)
            st.session_state["puntos_data"].clear()
            st.session_state["punto_en_edicion"] = "Punto 1"
            _init_punto_state()
            st.success("✅ Todo limpio")

    st.markdown("---")

    # ---------- Edición del Punto actual ----------
    p = st.session_state["punto_en_edicion"]
    st.markdown(f"### ✏️ Editando {p}")

    # Catálogos
    val_poste, lab_poste = _opciones_categoria(opciones, "Poste")
    val_pri,   lab_pri   = _opciones_categoria(opciones, "Primario")
    val_sec,   lab_sec   = _opciones_categoria(opciones, "Secundario")
    val_ret,   lab_ret   = _opciones_categoria(opciones, "Retenidas")
    val_ct,    lab_ct    = _opciones_categoria(opciones, "Conexiones a tierra")
    val_tr,    lab_tr    = _opciones_categoria(opciones, "Transformadores")

    # ===== FILA ÚNICA =====
    st.markdown("#### ➕ Agregar estructuras a este punto")
    cols = st.columns([2,2,2,2,2,2,1,1])

    with cols[0]:
        poste_sel = st.selectbox("Poste", [""] + val_poste, format_func=lambda x: lab_poste.get(x, x), key="poste_sel")
    with cols[1]:
        prim_sel = st.selectbox("Primario", [""] + val_pri, format_func=lambda x: lab_pri.get(x, x), key="prim_sel")
    with cols[2]:
        sec_sel = st.selectbox("Secundario", [""] + val_sec, format_func=lambda x: lab_sec.get(x, x), key="sec_sel")
    with cols[3]:
        ret_sel = st.selectbox("Retenidas", [""] + val_ret, format_func=lambda x: lab_ret.get(x, x), key="ret_sel")
    with cols[4]:
        tierra_sel = st.selectbox("Tierra", [""] + val_ct, format_func=lambda x: lab_ct.get(x, x), key="tierra_sel")
    with cols[5]:
        tr_sel = st.selectbox("Transformador", [""] + val_tr, format_func=lambda x: lab_tr.get(x, x), key="tr_sel")
    with cols[6]:
        cant = st.number_input("Cant.", min_value=1, step=1, value=1, key="cant_sel")

    with cols[7]:
        if st.button("➕ Agregar todo", type="primary", key="add_all"):
            if poste_sel:  add_item("Poste", poste_sel, cant)
            if prim_sel:   add_item("Primario", prim_sel, cant)
            if sec_sel:    add_item("Secundario", sec_sel, cant)
            if ret_sel:    add_item("Retenidas", ret_sel, cant)
            if tierra_sel: add_item("Conexiones a tierra", tierra_sel, cant)
            if tr_sel:     add_item("Transformadores", tr_sel, cant)

            for k in ["poste_sel", "prim_sel", "sec_sel", "ret_sel", "tierra_sel", "tr_sel", "cant_sel"]:
                st.session_state.pop(k, None)

            st.success("✅ ¡Se agregó la fila completa!")
            st.rerun()

    st.markdown("---")

    # ---------- Vista consolidada del punto ----------
    st.markdown("#### 📑 Vista de estructuras / materiales (consolidado)")
    data_row = _consolidado_a_fila(p)
    st.dataframe(pd.DataFrame([data_row]), use_container_width=True, hide_index=True)

    # ---------- Guardar punto ----------
    if st.button("💾 Guardar Estructura del Punto", type="primary"):
        fila = _consolidado_a_fila(p)
        df = st.session_state["df_puntos"]
        df = df[df["Punto"] != p]
        st.session_state["df_puntos"] = pd.concat([df, pd.DataFrame([fila])], ignore_index=True)
        st.success("✅ Punto guardado")

    # Tabla completa
    df_all = st.session_state["df_puntos"]
    if not df_all.empty:
        st.markdown("#### 🗂️ Puntos del proyecto")
        st.dataframe(df_all, use_container_width=True, hide_index=True)

    return df_all



# ==============================
# Despachador por modo
# ==============================
def seccion_entrada_estructuras(modo_carga: str):
    """Despacha al modo de carga seleccionado."""
    df = pd.DataFrame(columns=COLUMNAS_BASE)
    ruta_estructuras = None

    if modo_carga == "Desde archivo Excel":
        df, ruta_estructuras = cargar_desde_excel()
    elif modo_carga == "Pegar tabla":
        df = pegar_tabla()
    elif modo_carga == "Listas desplegables":
        df = listas_desplegables()

    return df, ruta_estructuras
