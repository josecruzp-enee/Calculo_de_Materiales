# interfaz/estructuras_desplegables.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Tuple
import re

import pandas as pd
import streamlit as st

# Comunes (ANCHO -> LARGO)
from interfaz.estructuras_comunes import (
    COLUMNAS_BASE,
    normalizar_columnas,
    expand_wide_to_long,
    materializar_df_a_archivo,
)


# =============================================================================
# Catálogo (desde modulo.desplegables)
# =============================================================================
def _cargar_opciones_catalogo() -> Dict[str, Dict[str, object]]:
    try:
        from modulo.desplegables import cargar_opciones  # type: ignore
        opciones = cargar_opciones()
        # Asegurar llaves mínimas usadas por la UI
        for key in [
            "Poste", "Primario", "Secundario", "Retenidas",
            "Conexiones a tierra", "Transformadores", "Luminarias",
            "Protección", "Proteccion",
        ]:
            opciones.setdefault(key, {"valores": [], "etiquetas": {}})
            opciones[key].setdefault("valores", [])
            opciones[key].setdefault("etiquetas", {})
        return opciones
    except Exception:
        # Fallback mínimo (solo para no romper la UI)
        return {
            "Poste": {"valores": [], "etiquetas": {}},
            "Primario": {"valores": [], "etiquetas": {}},
            "Secundario": {"valores": [], "etiquetas": {}},
            "Retenidas": {"valores": [], "etiquetas": {}},
            "Conexiones a tierra": {"valores": [], "etiquetas": {}},
            "Transformadores": {"valores": [], "etiquetas": {}},
            "Luminarias": {"valores": [], "etiquetas": {}},
            "Protección": {"valores": [], "etiquetas": {}},
        }


def _pick_vals_labels(opciones: dict, prefer: list[str], fuzzy: list[str] | None = None):
    for k in prefer:
        blk = opciones.get(k)
        if blk and blk.get("valores"):
            vals = blk.get("valores", [])
            labs = blk.get("etiquetas", {}) or {c: c for c in vals}
            return vals, labs
    if fuzzy:
        for k, blk in opciones.items():
            k_low = str(k).lower()
            if any(f in k_low for f in fuzzy):
                if blk and blk.get("valores"):
                    vals = blk.get("valores", [])
                    labs = blk.get("etiquetas", {}) or {c: c for c in vals}
                    return vals, labs
    return [], {}


# =============================================================================
# Estado
# =============================================================================
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


# =============================================================================
# Helpers de consolidación
# =============================================================================
def _add_item(cat: str, code: str, qty: int):
    if not code or qty <= 0:
        return
    p = st.session_state["punto_en_edicion"]
    bucket = st.session_state["puntos_data"][p][cat]
    bucket[code] = bucket.get(code, 0) + int(qty)


def _remove_item(cat: str, code: str, all_qty: bool = False):
    p = st.session_state["punto_en_edicion"]
    bucket = st.session_state["puntos_data"][p][cat]
    if code in bucket:
        if all_qty or bucket[code] <= 1:
            bucket.pop(code, None)
        else:
            bucket[code] -= 1


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


# =============================================================================
# UI
# =============================================================================
def _fila_categoria_ui(cat_key: str, valores: list[str], etiquetas: dict, key_prefix: str,
                      display_label: str | None = None):
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
            " ",
            min_value=1, max_value=99, step=1, value=1,
            key=f"{key_prefix}_{cat_key}_qty",
            label_visibility="collapsed",
        )
    with c3:
        if st.button("➕ Agregar", key=f"{key_prefix}_{cat_key}_add"):
            _add_item(cat_key, sel, qty)


# =============================================================================
# Entrada principal (modo Desplegables)
# =============================================================================
def listas_desplegables() -> Tuple[pd.DataFrame | None, str | None]:
    """
    UI por listas desplegables.
    Retorna:
        df_largo (Punto, codigodeestructura, cantidad),
        ruta_tmp (xlsx temporal con ANCHO/LARGO).
    """
    _ensure_df_sesion()
    _ensure_punto()
    _ensure_consolidado()

    df_actual = st.session_state["df_puntos"]
    opciones = _cargar_opciones_catalogo()

    st.subheader("🏗️ Estructuras del Proyecto (Listas desplegables)")

    # Barra superior
    colA, colB, colC, colD = st.columns([1.2, 1.4, 1.8, 1.2])
    with colA:
        if st.button("🆕 Crear nuevo Punto"):
            existentes = df_actual["Punto"].tolist() if not df_actual.empty else []
            nums = []
            for p in existentes:
                m = re.search(r"(\d+)", str(p))
                if m:
                    nums.append(int(m.group(1)))
            nuevo = f"Punto {(max(nums) + 1) if nums else 1}"
            st.session_state["punto_en_edicion"] = nuevo
            _ensure_consolidado()

    with colB:
        if not df_actual.empty:
            p_sel = st.selectbox("📍 Ir a punto:", df_actual["Punto"].unique())
            if st.button("✏️ Editar"):
                st.session_state["punto_en_edicion"] = p_sel
                _ensure_consolidado()

    with colC:
        if not df_actual.empty:
            p_del = st.selectbox("❌ Borrar punto:", df_actual["Punto"].unique(), key="del_punto")
            if st.button("Borrar"):
                st.session_state["df_puntos"] = df_actual[df_actual["Punto"] != p_del].reset_index(drop=True)
                st.session_state["puntos_data"].pop(p_del, None)

    with colD:
        if st.button("🧹 Limpiar todo"):
            st.session_state["df_puntos"] = pd.DataFrame(columns=COLUMNAS_BASE)
            st.session_state["puntos_data"] = {}
            st.session_state["punto_en_edicion"] = "Punto 1"
            _ensure_consolidado()

    st.markdown("---")
    punto = st.session_state["punto_en_edicion"]
    st.markdown(f"### ✏️ Editando {punto}")

    # Catálogos
    vals_poste, lab_poste = _pick_vals_labels(opciones, ["Poste"], ["poste"])
    vals_pri, lab_pri = _pick_vals_labels(opciones, ["Primario"], ["primar", "mt"])
    vals_sec, lab_sec = _pick_vals_labels(opciones, ["Secundario"], ["secund", "bt"])
    vals_ret, lab_ret = _pick_vals_labels(opciones, ["Retenidas"], ["reten"])
    vals_ct,  lab_ct  = _pick_vals_labels(opciones, ["Conexiones a tierra"], ["tierra"])
    vals_tr,  lab_tr  = _pick_vals_labels(opciones, ["Transformadores"], ["trafo"])
    vals_lum, lab_lum = _pick_vals_labels(opciones, ["Luminarias"], ["lumin"])

    # Mezcla Tierra + Protección
    vals_prot, lab_prot = _pick_vals_labels(opciones, ["Protección", "Proteccion"], ["protec"])
    mix_vals, seen = [], set()
    for v in (vals_ct + vals_prot):
        vv = str(v).strip()
        if vv and vv not in seen:
            seen.add(vv)
            mix_vals.append(vv)
    mix_labs = {**(lab_ct or {}), **(lab_prot or {})} or {c: c for c in mix_vals}

    key_prefix = f"kp_{punto}"
    _fila_categoria_ui("Poste", vals_poste, lab_poste, key_prefix)
    _fila_categoria_ui("Primario", vals_pri, lab_pri, key_prefix)
    _fila_categoria_ui("Secundario", vals_sec, lab_sec, key_prefix)
    _fila_categoria_ui("Retenidas", vals_ret, lab_ret, key_prefix)
    _fila_categoria_ui("Luminarias", vals_lum, lab_lum, key_prefix)
    _fila_categoria_ui(
        "Conexiones a tierra", mix_vals, mix_labs,
        key_prefix + "_ctp", display_label="Conexiones a tierra / Protección"
    )
    _fila_categoria_ui("Transformadores", vals_tr, lab_tr, key_prefix)

    st.markdown("---")
    st.markdown("#### 📑 Vista consolidada del punto")
    fila = _consolidado_a_fila(punto)
    st.dataframe(pd.DataFrame([fila]), use_container_width=True, hide_index=True)

    if st.button("💾 Guardar Estructura del Punto", type="primary"):
        base = st.session_state["df_puntos"]
        if not base.empty:
            base = base[base["Punto"] != punto]
        st.session_state["df_puntos"] = pd.concat([base, pd.DataFrame([fila])], ignore_index=True)

    df_all_wide = st.session_state.get("df_puntos", pd.DataFrame(columns=COLUMNAS_BASE))
    if not df_all_wide.empty:
        df_all_wide = normalizar_columnas(df_all_wide, COLUMNAS_BASE)

        def _num_punto(x: str) -> int:
            m = re.search(r"(\d+)", str(x))
            return int(m.group(1)) if m else 10**9

        df_all_wide = df_all_wide.sort_values(
            by="Punto", key=lambda s: s.map(_num_punto)
        ).reset_index(drop=True)

        df_largo = expand_wide_to_long(df_all_wide)
        ruta_tmp = materializar_df_a_archivo(df_all_wide, "ui")

        return df_largo, ruta_tmp

    return None, None
