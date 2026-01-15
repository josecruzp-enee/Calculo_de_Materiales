# interfaz/estructuras_desplegables.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Tuple, Dict, List
import pandas as pd
import streamlit as st

# Importamos lo común desde estructuras.py
from interfaz.estructuras import (
    COLUMNAS_BASE,
    _normalizar_columnas,
    _materializar_df_a_archivo,
    _expand_wide_to_long,
)

# =============================================================================
# Desplegables (UI PRO) - TODO lo largo vive aquí
# =============================================================================

def _cargar_opciones_catalogo() -> Dict[str, Dict[str, object]]:
    """
    Intenta cargar opciones desde modulo.desplegables.cargar_opciones().
    """
    try:
        from modulo.desplegables import cargar_opciones  # type: ignore
        opciones = cargar_opciones()
        for key in ["Poste", "Primaria", "Primario", "Secundaria", "Secundario", "MT", "BT",
                    "Retenidas", "Conexiones a tierra", "Transformadores", "Transformador", "Luminarias",
                    "Protección", "Proteccion"]:
            opciones.setdefault(key, {"valores": [], "etiquetas": {}})
            opciones[key].setdefault("valores", [])
            opciones[key].setdefault("etiquetas", {})
        return opciones
    except Exception:
        return {
            "Poste": {"valores": ["PM-40 (E)", "PC-40 (E)"], "etiquetas": {}},
            "MT": {"valores": ["A-I-1 (E)", "A-II-5 (E)", "A-III-7 (E)"], "etiquetas": {}},
            "BT": {"valores": ["B-I-1 (R)", "B-II-4C (R)", "B-II-6A (R)"], "etiquetas": {}},
            "Retenidas": {"valores": ["R-1 (E)", "R-4 (D)", "R-5T (E)"], "etiquetas": {}},
            "Conexiones a tierra": {"valores": ["CT-N (P)", "CT-N (E)"], "etiquetas": {}},
            "Transformadores": {"valores": ["TD (P)", "25 kVA", "50 kVA"], "etiquetas": {}},
            "Luminarias": {"valores": ["LL-1"], "etiquetas": {}},
            "Protección": {"valores": [], "etiquetas": {}},
        }

def _pick_vals_labels(opciones: dict, prefer: List[str], fuzzy: List[str] | None = None):
    for k in prefer:
        blk = opciones.get(k)
        if blk and blk.get("valores"):
            vals = blk.get("valores", [])
            labs = blk.get("etiquetas", {}) or {}
            if not labs:
                labs = {c: c for c in vals}
            return vals, labs
    if fuzzy:
        for k, blk in opciones.items():
            k_low = str(k).lower()
            if any(f in k_low for f in fuzzy):
                if blk and blk.get("valores"):
                    vals = blk.get("valores", [])
                    labs = blk.get("etiquetas", {}) or {}
                    if not labs:
                        labs = {c: c for c in vals}
                    return vals, labs
    return [], {}

def _ensure_df_sesion():
    if "df_puntos" not in st.session_state:
        st.session_state["df_puntos"] = pd.DataFrame(columns=COLUMNAS_BASE)

def _ensure_punto():
    if "punto_en_edicion" not in st.session_state:
        df = st.session_state.get("df_puntos", pd.DataFrame())
        st.session_state["punto_en_edicion"] = df["Punto"].iloc[0] if isinstance(df, pd.DataFrame) and not df.empty else "Punto 1"

def _ensure_consolidado():
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
            "Luminarias": {},
        }

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

def _fila_categoria_ui(cat_key: str, valores: list[str], etiquetas: dict, key_prefix: str, display_label: str | None = None):
    label = display_label or cat_key
    st.markdown(f"**{label}**")

    c1, c2, c3 = st.columns([7, 1.1, 1.9])
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
            st.success(f"Añadido: {qty}× {etiquetas.get(sel, sel)}")

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

def listas_desplegables() -> Tuple[pd.DataFrame | None, str | None]:
    """UI PRO con desplegables; guarda en sesión (ANCHO) y retorna (LARGO, ruta)."""
    _ensure_df_sesion()
    _ensure_punto()
    _ensure_consolidado()

    df_actual = st.session_state["df_puntos"]
    opciones = _cargar_opciones_catalogo()

    st.subheader("🏗️ Estructuras del Proyecto (Desplegables)")

    # Barra superior
    colA, colB, colC, colD = st.columns([1.2, 1.2, 1.8, 1.2])
    with colA:
        if st.button("🆕 Crear nuevo Punto"):
            existentes = df_actual["Punto"].unique().tolist() if not df_actual.empty else []
            nums = []
            for p in existentes:
                try:
                    n = int(pd.to_numeric(pd.Series(p).str.extract(r"(\d+)")[0]).iloc[0])
                    nums.append(n)
                except Exception:
                    pass
            nuevo = f"Punto {(max(nums) + 1) if nums else 1}"
            st.session_state["punto_en_edicion"] = nuevo
            _ensure_consolidado()
            st.success(f"✏️ {nuevo} creado y listo para editar")

    with colB:
        if not df_actual.empty:
            p_sel = st.selectbox("📍 Ir a punto:", df_actual["Punto"].unique(), key="sel_goto_punto")
            if st.button("✏️ Editar", key="btn_editar_punto"):
                st.session_state["punto_en_edicion"] = p_sel
                _ensure_consolidado()
                st.success(f"✏️ Editando {p_sel}")

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
            st.session_state["puntos_data"] = {}
            st.session_state["punto_en_edicion"] = "Punto 1"
            _ensure_consolidado()
            st.success("✅ Se limpiaron todas las estructuras/materiales")

    st.markdown("---")
    punto = st.session_state["punto_en_edicion"]
    st.markdown(f"### ✏️ Editando {punto}")

    # Catálogos base
    vals_poste, lab_poste = _pick_vals_labels(opciones, ["Poste"], ["poste"])
    vals_pri, lab_pri = _pick_vals_labels(opciones, ["Primario", "Primaria", "MT", "Media Tensión", "Media Tension"], ["primar", "media", "mt"])
    vals_sec, lab_sec = _pick_vals_labels(opciones, ["Secundario", "Secundaria", "BT", "Baja Tensión", "Baja Tension"], ["secund", "baja", "bt"])
    vals_ret, lab_ret = _pick_vals_labels(opciones, ["Retenidas"], ["reten"])
    vals_ct, lab_ct = _pick_vals_labels(opciones, ["Conexiones a tierra", "Tierra"], ["tierra"])
    vals_tr, lab_tr = _pick_vals_labels(opciones, ["Transformadores", "Transformador"], ["trafo", "transfor"])
    vals_lum, lab_lum = _pick_vals_labels(opciones, ["Luminarias", "Luminaria"], ["lumin"])

    # Mezcla tierra + protección (si existe)
    vals_prot, lab_prot = _pick_vals_labels(opciones, ["Protección", "Proteccion"], ["protec"])
    mix_vals, seen = [], set()
    for v in (vals_ct + vals_prot):
        vv = str(v).strip()
        if vv and vv not in seen:
            seen.add(vv)
            mix_vals.append(vv)
    mix_labs = {}
    mix_labs.update(lab_ct or {})
    mix_labs.update(lab_prot or {})
    if not mix_labs:
        mix_labs = {c: c for c in mix_vals}

    # UI filas
    key_prefix = f"kp_{punto}"
    _fila_categoria_ui("Poste", vals_poste, lab_poste, key_prefix)
    _fila_categoria_ui("Primario", vals_pri, lab_pri, key_prefix)
    _fila_categoria_ui("Secundario", vals_sec, lab_sec, key_prefix)
    _fila_categoria_ui("Retenidas", vals_ret, lab_ret, key_prefix)
    _fila_categoria_ui("Luminarias", vals_lum, lab_lum, key_prefix)
    _fila_categoria_ui(
        cat_key="Conexiones a tierra",
        valores=mix_vals,
        etiquetas=mix_labs,
        key_prefix=key_prefix + "_ctp",
        display_label="Conexiones a tierra / Protección",
    )
    _fila_categoria_ui("Transformadores", vals_tr, lab_tr, key_prefix)

    st.markdown("---")
    st.markdown("#### 📑 Vista consolidada del punto")
    row = _consolidado_a_fila(punto)
    st.dataframe(pd.DataFrame([row]), use_container_width=True, hide_index=True)

    st.markdown("##### ✂️ Editar seleccionados")
    cols = st.columns(3)
    with cols[0]:
        cat = st.selectbox("Categoría", ["Poste", "Primario", "Secundario", "Retenidas", "Conexiones a tierra", "Transformadores", "Luminarias"], key="chip_cat")
    with cols[1]:
        codes = list(st.session_state["puntos_data"][punto][cat].keys())
        code = st.selectbox("Código", codes, key="chip_code")
    with cols[2]:
        c1, c2 = st.columns(2)
        if c1.button("– Restar uno", key="chip_minus"):
            _remove_item(cat, code, all_qty=False)
        if c2.button("🗑 Eliminar todo", key="chip_del"):
            _remove_item(cat, code, all_qty=True)

    st.markdown("---")
    if st.button("💾 Guardar Estructura del Punto", type="primary", key="btn_guardar_estructura"):
        fila = _consolidado_a_fila(punto)
        base = st.session_state["df_puntos"]
        if not base.empty:
            base = base[base["Punto"] != punto]
        st.session_state["df_puntos"] = pd.concat([base, pd.DataFrame([fila])], ignore_index=True)
        st.success("✅ Punto guardado")

    df_all_wide = st.session_state.get("df_puntos", pd.DataFrame(columns=COLUMNAS_BASE))
    if not df_all_wide.empty:
        st.markdown("#### 🗂️ Puntos del proyecto")
        st.dataframe(df_all_wide.sort_values(by="Punto"), use_container_width=True, hide_index=True)

    if isinstance(df_all_wide, pd.DataFrame) and not df_all_wide.empty:
        df_all_wide = _normalizar_columnas(df_all_wide, COLUMNAS_BASE)
        ruta_tmp = _materializar_df_a_archivo(df_all_wide, "ui")
        df_largo = _expand_wide_to_long(df_all_wide)
        return df_largo, ruta_tmp

    return None, None
