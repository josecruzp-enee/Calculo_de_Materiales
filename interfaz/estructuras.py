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
        # primer punto por defecto si no existe ninguno
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
        "Primaria": {...}, "Secundaria": {...}, "Retenidas": {...},
        "Conexiones a tierra": {...}, "Transformadores": {...}
      }
    """
    bloque = opciones_dict.get(llave_catalogo) or {}
    valores = bloque.get("valores", []) or []
    etiquetas = bloque.get("etiquetas", {}) or {}
    return valores, etiquetas


def fila_categoria(label: str, valores: list[str], etiquetas: dict, key_prefix: str):
    """Fila compacta: select + cantidad mini + botón Agregar."""
    st.markdown(f"**{label}**")
    c1, c2, c3 = st.columns([7, 1.1, 1.9])  # ajusta proporciones a tu ancho

    with c1:
        sel = st.selectbox(
            "", valores,
            index=0 if valores else None,
            key=f"{key_prefix}_sel",
            label_visibility="collapsed",
            format_func=lambda x: etiquetas.get(x, x),
        )
    with c2:
        qty = st.number_input(
            " ", min_value=1, max_value=99, step=1, value=1,
            key=f"{key_prefix}_qty", label_visibility="collapsed"
        )
    with c3:
        if st.button("➕ Agregar", key=f"{key_prefix}_add"):
            add_item(label, sel, qty)
            st.success(f"Añadido: {qty}× {etiquetas.get(sel, sel)}")


def _consolidado_a_fila(punto: str) -> dict:
    """Devuelve una fila compatible con COLUMNAS_BASE a partir del dict consolidado."""
    return {
        "Punto": punto,
        "Poste": render_cat_str(punto, "Poste"),
        "Primario": render_cat_str(punto, "Primario"),
        "Secundario": render_cat_str(punto, "Secundario"),
        "Retenidas": render_cat_str(punto, "Retenidas"),
        "Conexiones a tierra": render_cat_str(punto, "Conexiones a tierra"),
        "Transformadores": render_cat_str(punto, "Transformadores"),
    }


def listas_desplegables():
    """
    UI de edición por Punto con select + cantidad + agregar (no elimina
    opciones del desplegable y permite 2× del mismo código).
    """
    from modulo.desplegables import cargar_opciones
    opciones = cargar_opciones()  # lee 'indice' y arma {"valores": [...], "etiquetas": {...}}

    st.subheader("3. 🏗️ Estructuras del Proyecto")

    _init_punto_state()
    df_actual = st.session_state["df_puntos"]

    # ---------- Barra superior: crear/editar/borrar punto ----------
    colA, colB, colC, colD = st.columns([1.2, 1.2, 1.8, 1.2])
    with colA:
        if st.button("🆕 Crear nuevo Punto"):
            # siguiente número
            existentes = df_actual["Punto"].unique().tolist() if not df_actual.empty else []
            nums = []
            for p in existentes:
                try:
                    nums.append(int(pd.to_numeric(pd.Series(p).str.extract(r"(\d+)")[0]).iloc[0]))
                except Exception:
                    pass
            nuevo_num = (max(nums) + 1) if nums else 1
            nuevo = f"Punto {nuevo_num}"
            st.session_state["punto_en_edicion"] = nuevo
            # reset contenedor del nuevo punto
            st.session_state["puntos_data"][nuevo] = {
                "Poste": {}, "Primario": {}, "Secundario": {},
                "Retenidas": {}, "Conexiones a tierra": {}, "Transformadores": {}
            }
            st.success(f"✏️ {nuevo} creado y listo para editar")
            resetear_desplegables()
    with colB:
        if not df_actual.empty:
            p_sel = st.selectbox("📍 Ir a punto:", df_actual["Punto"].unique(), key="sel_goto_punto")
            if st.button("✏️ Editar", key="btn_editar_punto"):
                st.session_state["punto_en_edicion"] = p_sel
                # si existe fila previa, parsearla a dict consolidado básico (opcional)
                if p_sel not in st.session_state["puntos_data"]:
                    st.session_state["puntos_data"][p_sel] = {k: {} for k in
                        ["Poste","Primario","Secundario","Retenidas","Conexiones a tierra","Transformadores"]}
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
            st.success("✅ Se limpiaron todas las estructuras/materiales")

    st.markdown("---")

    # ---------- Edición del Punto actual ----------
    p = st.session_state["punto_en_edicion"]
    st.markdown(f"### ✏️ Editando {p}")

    # Catálogos desde tus opciones (ojo: 'Primaria' -> 'Primario')
    val_poste, lab_poste = _opciones_categoria(opciones, "Poste")
    val_pri,   lab_pri   = _opciones_categoria(opciones, "Primaria")
    val_sec,   lab_sec   = _opciones_categoria(opciones, "Secundaria")
    val_ret,   lab_ret   = _opciones_categoria(opciones, "Retenidas")
    val_ct,    lab_ct    = _opciones_categoria(opciones, "Conexiones a tierra")
    val_tr,    lab_tr    = _opciones_categoria(opciones, "Transformadores")

    fila_categoria("Poste", val_poste, lab_poste, "poste")
    fila_categoria("Primario", val_pri, lab_pri, "primario")
    fila_categoria("Secundario", val_sec, lab_sec, "secundario")
    fila_categoria("Retenidas", val_ret, lab_ret, "retenidas")
    fila_categoria("Conexiones a tierra", val_ct, lab_ct, "ctierra")
    fila_categoria("Transformadores", val_tr, lab_tr, "trafo")

    st.markdown("---")

    # ---------- Vista consolidada del punto ----------
    st.markdown("#### 📑 Vista de estructuras / materiales (consolidado)")
    data_row = _consolidado_a_fila(p)
    st.dataframe(pd.DataFrame([data_row]), use_container_width=True, hide_index=True)

    # ---------- Edición rápida (restar/eliminar) ----------
    st.markdown("##### ✂️ Editar seleccionados")
    cols = st.columns(3)
    with cols[0]:
        cat = st.selectbox("Categoría", ["Poste","Primario","Secundario","Retenidas","Conexiones a tierra","Transformadores"], key="chip_cat")
    with cols[1]:
        codes = list(st.session_state["puntos_data"][p][cat].keys())
        code = st.selectbox("Código", codes, key="chip_code")
    with cols[2]:
        c1, c2 = st.columns(2)
        if c1.button("– Restar uno", key="chip_minus"):
            remove_item(cat, code, all_qty=False)
        if c2.button("🗑 Eliminar todo", key="chip_del"):
            remove_item(cat, code, all_qty=True)

    st.markdown("---")

    # Guardar punto en df_puntos (reemplaza la fila del punto)
    if st.button("💾 Guardar Estructura del Punto", type="primary", key="btn_guardar_estructura"):
        fila = _consolidado_a_fila(p)
        df = st.session_state["df_puntos"]
        if not df.empty:
            df = df[df["Punto"] != p]
        st.session_state["df_puntos"] = pd.concat([df, pd.DataFrame([fila])], ignore_index=True)
        st.success("✅ Punto guardado")

    # Mostrar tabla completa de puntos
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
