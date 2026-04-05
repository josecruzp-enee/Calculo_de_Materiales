# -*- coding: utf-8 -*-
# interfaz/estructuras_desplegables.py

from __future__ import annotations
from typing import Dict, Tuple
import re

import pandas as pd
import streamlit as st

from interfaz.estructuras_comunes import (
    COLUMNAS_BASE,
    normalizar_columnas,
    expand_wide_to_long,
    materializar_df_a_archivo,
)


# =========================================================
# CATÁLOGO
# =========================================================
def _cargar_opciones_catalogo() -> Dict[str, Dict[str, object]]:
    from interfaz.desplegables import cargar_opciones, RUTA_EXCEL

    opciones = cargar_opciones(RUTA_EXCEL) or {}

    for key in [
        "Poste", "Primario", "Secundario", "Retenidas",
        "Conexiones a tierra", "Transformadores", "Luminarias",
        "Protección", "Proteccion",
    ]:
        opciones.setdefault(key, {"valores": [], "etiquetas": {}})
        opciones[key].setdefault("valores", [])
        opciones[key].setdefault("etiquetas", {})

    return opciones


def _pick_vals_labels(opciones: dict, prefer: list[str], fuzzy: list[str] | None = None):
    for k in prefer:
        blk = opciones.get(k)
        if blk and blk.get("valores"):
            vals = blk.get("valores", [])
            labs = blk.get("etiquetas", {}) or {c: c for c in vals}
            return vals, labs

    if fuzzy:
        for k, blk in opciones.items():
            if any(f in str(k).lower() for f in fuzzy):
                if blk and blk.get("valores"):
                    vals = blk.get("valores", [])
                    labs = blk.get("etiquetas", {}) or {c: c for c in vals}
                    return vals, labs

    return [], {}


# =========================================================
# ESTADO
# =========================================================
def _ensure_df_sesion():
    st.session_state.setdefault("df_puntos", pd.DataFrame(columns=COLUMNAS_BASE))


def _ensure_punto():
    if "punto_en_edicion" not in st.session_state:
        df = st.session_state.get("df_puntos")
        st.session_state["punto_en_edicion"] = (
            df["Punto"].iloc[0] if isinstance(df, pd.DataFrame) and not df.empty else "Punto 1"
        )


def _ensure_consolidado():
    st.session_state.setdefault("puntos_data", {})
    p = st.session_state["punto_en_edicion"]

    st.session_state["puntos_data"].setdefault(
        p,
        {
            "Poste": {},
            "Primario": {},
            "Secundario": {},
            "Retenidas": {},
            "Conexiones a tierra": {},
            "Transformadores": {},
            "Luminarias": {},
        },
    )


# =========================================================
# HELPERS
# =========================================================
def _fix_codigo(c):
    s = str(c).upper().strip()

    match = re.search(r"(TS|TD|TT)-\d+(\.\d+)?", s)
    if match:
        base = match.group(0)
        return base + "KVA"

    return s.split(" - ")[0].strip()


def _add_item(cat: str, code: str, qty: int):
    if not code or qty <= 0:
        return

    code = _fix_codigo(code)

    p = st.session_state["punto_en_edicion"]
    bucket = st.session_state["puntos_data"][p][cat]

    bucket[code] = bucket.get(code, 0) + int(qty)


def _render_cat_str(punto: str, categoria: str) -> str:
    data = st.session_state["puntos_data"][punto][categoria]
    if not data:
        return ""

    parts = []
    for code, n in data.items():
        parts.append(f"{n}× {code}" if n > 1 else code)

    return ", ".join(parts)


def _consolidado_a_fila(punto: str) -> Dict[str, str]:
    return {
        "Punto": punto,
        "Poste": _render_cat_str(punto, "Poste"),
        "Primario": _render_cat_str(punto, "Primario"),
        "Secundario": _render_cat_str(punto, "Secundario"),
        "Retenidas": _render_cat_str(punto, "Retenidas"),
        "Conexiones a tierra": _render_cat_str(punto, "Conexiones a tierra"),
        "Transformadores": _render_cat_str(punto, "Transformadores"),
        "Luminarias": _render_cat_str(punto, "Luminarias"),
    }


# =========================================================
# UI
# =========================================================
def _fila_categoria_ui(cat_key, valores, etiquetas, key_prefix, display_label=None):

    label = display_label or cat_key
    st.markdown(f"**{label}**")

    c1, c2, c3 = st.columns([7, 1.2, 2])

    with c1:
        sel = st.selectbox(
            "",
            valores,
            index=0 if valores else None,
            key=f"{key_prefix}_{cat_key}_sel",
            label_visibility="collapsed",
            format_func=lambda x: etiquetas.get(x, x),
        )

    with c2:
        qty = st.number_input(
            "",
            min_value=1,
            max_value=99,
            step=1,
            value=1,
            key=f"{key_prefix}_{cat_key}_qty",
            label_visibility="collapsed",
        )

    with c3:
        if st.button("➕", key=f"{key_prefix}_{cat_key}_add"):
            _add_item(cat_key, sel, qty)


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================
def listas_desplegables() -> Tuple[pd.DataFrame | None, str | None]:

    _ensure_df_sesion()
    _ensure_punto()
    _ensure_consolidado()

    df_actual = st.session_state["df_puntos"]
    opciones = _cargar_opciones_catalogo()

    st.subheader("🏗️ Estructuras del Proyecto")

    colA, colB, colC, colD = st.columns([1.2, 1.4, 1.8, 1.2])

    with colA:
        if st.button("🆕 Punto"):
            nums = [
                int(re.search(r"\d+", str(p)).group())
                for p in df_actual["Punto"]
                if re.search(r"\d+", str(p))
            ] if not df_actual.empty else []

            nuevo = f"Punto {(max(nums) + 1) if nums else 1}"
            st.session_state["punto_en_edicion"] = nuevo
            _ensure_consolidado()

    with colB:
        if not df_actual.empty:
            p_sel = st.selectbox("Ir a:", df_actual["Punto"].unique())
            if st.button("Editar"):
                st.session_state["punto_en_edicion"] = p_sel

    with colC:
        if not df_actual.empty:
            p_del = st.selectbox("Eliminar:", df_actual["Punto"].unique())
            if st.button("Borrar"):
                st.session_state["df_puntos"] = df_actual[df_actual["Punto"] != p_del]
                st.session_state["puntos_data"].pop(p_del, None)

    with colD:
        if st.button("🧹 Reset"):
            st.session_state["df_puntos"] = pd.DataFrame(columns=COLUMNAS_BASE)
            st.session_state["puntos_data"] = {}
            st.session_state["punto_en_edicion"] = "Punto 1"

    punto = st.session_state["punto_en_edicion"]
    st.markdown(f"### {punto}")

    vals_poste, lab_poste = _pick_vals_labels(opciones, ["Poste"])
    vals_pri, lab_pri = _pick_vals_labels(opciones, ["Primario"])
    vals_sec, lab_sec = _pick_vals_labels(opciones, ["Secundario"])
    vals_ret, lab_ret = _pick_vals_labels(opciones, ["Retenidas"])
    vals_ct, lab_ct = _pick_vals_labels(opciones, ["Conexiones a tierra"])
    vals_tr, lab_tr = _pick_vals_labels(opciones, ["Transformadores"])
    vals_lum, lab_lum = _pick_vals_labels(opciones, ["Luminarias"])

    kp = f"kp_{punto}"

    _fila_categoria_ui("Poste", vals_poste, lab_poste, kp)
    _fila_categoria_ui("Primario", vals_pri, lab_pri, kp)
    _fila_categoria_ui("Secundario", vals_sec, lab_sec, kp)
    _fila_categoria_ui("Retenidas", vals_ret, lab_ret, kp)
    _fila_categoria_ui("Conexiones a tierra", vals_ct, lab_ct, kp)
    _fila_categoria_ui("Transformadores", vals_tr, lab_tr, kp)
    _fila_categoria_ui("Luminarias", vals_lum, lab_lum, kp)

    fila = _consolidado_a_fila(punto)
    st.dataframe(pd.DataFrame([fila]), use_container_width=True, hide_index=True)

    if st.button("💾 Guardar"):
        base = st.session_state["df_puntos"]
        base = base[base["Punto"] != punto] if not base.empty else base
        st.session_state["df_puntos"] = pd.concat([base, pd.DataFrame([fila])], ignore_index=True)

    df_all = st.session_state["df_puntos"]

    if not df_all.empty:
        df_all = normalizar_columnas(df_all, COLUMNAS_BASE)
        df_largo = expand_wide_to_long(df_all)
        ruta = materializar_df_a_archivo(df_all, "ui")
        return df_largo, ruta

    return None, None
