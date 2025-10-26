# interfaz/estructuras.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import io
from typing import Optional, Tuple, List, Dict

import pandas as pd
import streamlit as st

# =============================================================================
# Esquema base y utilidades
# =============================================================================

COLUMNAS_BASE: List[str] = [
    "Punto",
    "Poste",
    "Primario",
    "Secundario",
    "Retenidas",
    "Conexiones a tierra",
    "Transformadores",
]

def _normalizar_columnas(df: pd.DataFrame, columnas: List[str]) -> pd.DataFrame:
    df = df.copy()
    for c in columnas:
        if c not in df.columns:
            df[c] = ""
    return df[columnas]

def _parsear_texto_a_df(texto: str, columnas: List[str]) -> pd.DataFrame:
    txt = (texto or "").strip()
    if not txt:
        return pd.DataFrame(columns=columnas)
    df = None
    for sep in ("\t", ",", ";", "|"):
        try:
            df = pd.read_csv(io.StringIO(txt), sep=sep)
            break
        except Exception:
            df = None
    if df is None:
        try:
            df = pd.read_csv(io.StringIO(txt), delim_whitespace=True)
        except Exception:
            return pd.DataFrame(columns=columnas)
    return _normalizar_columnas(df, columnas)

# =============================================================================
# Modo: Excel
# =============================================================================

def cargar_desde_excel() -> Tuple[pd.DataFrame | None, str | None]:
    archivo = st.file_uploader("Archivo de estructuras (.xlsx)", type=["xlsx"], key="upl_estructuras")
    if not archivo:
        return None, None
    nombre = getattr(archivo, "name", "estructura_lista.xlsx")
    try:
        df = pd.read_excel(archivo)
    except Exception as e:
        st.error(f"Error leyendo el Excel: {e}")
        return None, nombre
    df = _normalizar_columnas(df, COLUMNAS_BASE)
    st.success(f"✅ Cargadas {len(df)} filas desde {nombre}")
    return df, nombre

# =============================================================================
# Modo: Pegar tabla (CSV/TSV)
# =============================================================================

def pegar_tabla() -> Tuple[pd.DataFrame | None, str | None]:
    texto_pegado = st.text_area("Pega aquí tu tabla (CSV/TSV)", height=200, key="txt_pegar_tabla")
    if not texto_pegado:
        return None, None
    df = _parsear_texto_a_df(texto_pegado, COLUMNAS_BASE)
    st.success(f"✅ Tabla cargada con {len(df)} filas")
    return df, "PEGA/TEXTO"

# =============================================================================
# Modo: Desplegables (Listas PRO) con MT/BT
# =============================================================================

def _cargar_opciones_catalogo() -> Dict[str, Dict[str, object]]:
    """
    Intenta cargar opciones desde modulo.desplegables.cargar_opciones().
    Estructura esperada por categoría:
      {"valores": [cod1, cod2, ...], "etiquetas": {cod1: "cod1 – desc", ...}}
    Si no existe el módulo, retorna un fallback mínimo.
    """
    try:
        from modulo.desplegables import cargar_opciones  # type: ignore
        opciones = cargar_opciones()
        # Normalización suave
        for key in ["Poste", "Primaria", "Primario", "Secundaria", "Secundario", "MT", "BT",
                    "Retenidas", "Conexiones a tierra", "Transformadores", "Transformador"]:
            opciones.setdefault(key, {"valores": [], "etiquetas": {}})
            opciones[key].setdefault("valores", [])
            opciones[key].setdefault("etiquetas", {})
        return opciones
    except Exception:
        # Fallback simple
        return {
            "Poste": {"valores": ["PC-40", "PM-35"], "etiquetas": {
                "PC-40": "PC-40 – Poste de Concreto de 40 Pies.",
                "PM-35": "PM-35 – Poste de Madera de 35 Pies.",
            }},
            "MT": {"valores": ["1/0 ACSR", "3/0 ACSR", "4/0 ACSR"], "etiquetas": {}},
            "BT": {"valores": ["#2 ACSR", "1/0 ACSR"], "etiquetas": {}},
            "Retenidas": {"valores": ["R-0", "R-1", "R-2"], "etiquetas": {
                "R-1": "R-1 – Estructura Secundaria dos Fase en triple remate."
            }},
            "Conexiones a tierra": {"valores": ['CT-N', 'Varilla 5/8" x 8\'', "Malla"], "etiquetas": {
                "CT-N": "CT-N – Conexión Tierra a Neutro."
            }},
            "Transformadores": {"valores": ["TD", "25 kVA", "37.5 kVA", "50 kVA"], "etiquetas": {
                "TD": "TD – Estructura Secundaria dos Fase en triple remate."
            }},
        }

def _pick_vals_labels(opciones: dict, prefer: list[str], fuzzy_fragments: list[str] | None = None):
    """
    Devuelve (valores, etiquetas) probando primero claves 'prefer' y luego
    una búsqueda suave por fragmentos (fuzzy).
    """
    for k in prefer:
        blk = opciones.get(k)
        if blk and blk.get("valores"):
            vals = blk.get("valores", [])
            labs = blk.get("etiquetas", {}) or {}
            if not labs:
                labs = {c: c for c in vals}
            return vals, labs
    if fuzzy_fragments:
        for k, blk in opciones.items():
            k_low = str(k).lower()
            if any(f in k_low for f in fuzzy_fragments):
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

def _ensure_punto_en_edicion():
    if "punto_en_edicion" not in st.session_state:
        df = st.session_state.get("df_puntos", pd.DataFrame())
        st.session_state["punto_en_edicion"] = df["Punto"].iloc[0] if isinstance(df, pd.DataFrame) and not df.empty else "Punto 1"

def _ensure_data_consolidada():
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

def _fila_categoria_ui(label: str, valores: list[str], etiquetas: dict, key_prefix: str):
    st.markdown(f"**{label}**")
    c1, c2, c3 = st.columns([7, 1.1, 1.9])
    with c1:
        sel = st.selectbox(
            "", valores, index=0 if valores else None,
            key=f"{key_prefix}_{label}_sel",
            label_visibility="collapsed",
            format_func=lambda x: etiquetas.get(x, x),
        )
    with c2:
        qty = st.number_input(
            " ", min_value=1, max_value=99, step=1, value=1,
            key=f"{key_prefix}_{label}_qty", label_visibility="collapsed"
        )
    with c3:
        if st.button("➕ Agregar", key=f"{key_prefix}_{label}_add"):
            _add_item(label, sel, qty)
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
    }

def listas_desplegables() -> Tuple[pd.DataFrame | None, str | None]:
    """
    UI PRO con desplegables (MT/BT, Primario/Secundario) + cantidad.
    Consolida por Punto y guarda en st.session_state["df_puntos"].
    """
    _ensure_df_sesion()
    _ensure_punto_en_edicion()
    _ensure_data_consolidada()

    df_actual = st.session_state["df_puntos"]
    punto = st.session_state["punto_en_edicion"]
    opciones = _cargar_opciones_catalogo()

    st.subheader("🏗️ Estructuras del Proyecto (Desplegables)")

    # ---- Barra superior ----
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
            _ensure_data_consolidada()
            st.success(f"✏️ {nuevo} creado y listo para editar")

    with colB:
        if not df_actual.empty:
            p_sel = st.selectbox("📍 Ir a punto:", df_actual["Punto"].unique(), key="sel_goto_punto")
            if st.button("✏️ Editar", key="btn_editar_punto"):
                st.session_state["punto_en_edicion"] = p_sel
                _ensure_data_consolidada()
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
            _ensure_data_consolidada()
            st.success("✅ Se limpiaron todas las estructuras/materiales")

    st.markdown("---")
    # ---- Editor actual ----
    punto = st.session_state["punto_en_edicion"]
    st.markdown(f"### ✏️ Editando {punto}")

    # MT/BT y variantes + Primario/Secundario
    vals_poste, lab_poste = _pick_vals_labels(opciones, ["Poste"], ["poste"])

    vals_pri, lab_pri = _pick_vals_labels(
        opciones,
        prefer=["Primario", "Primaria", "MT", "Media Tensión", "Media Tension", "MT Primario", "Primaria MT"],
        fuzzy_fragments=["primar", "media", "mt"]
    )

    vals_sec, lab_sec = _pick_vals_labels(
        opciones,
        prefer=["Secundario", "Secundaria", "BT", "Baja Tensión", "Baja Tension", "BT Secundario", "Secundaria BT"],
        fuzzy_fragments=["secund", "baja", "bt"]
    )

    vals_ret, lab_ret = _pick_vals_labels(opciones, ["Retenidas"], ["reten"])
    vals_ct,  lab_ct  = _pick_vals_labels(opciones, ["Conexiones a tierra", "Tierra", "Puesta a tierra"], ["tierra", "puesta"])
    vals_tr,  lab_tr  = _pick_vals_labels(opciones, ["Transformadores", "Transformador"], ["trafo", "transfor"])

    key_prefix = f"kp_{punto}"

    _fila_categoria_ui("Poste",                 vals_poste, lab_poste, key_prefix)
    _fila_categoria_ui("Primario",              vals_pri,   lab_pri,   key_prefix)
    _fila_categoria_ui("Secundario",            vals_sec,   lab_sec,   key_prefix)
    _fila_categoria_ui("Retenidas",             vals_ret,   lab_ret,   key_prefix)
    _fila_categoria_ui("Conexiones a tierra",   vals_ct,    lab_ct,    key_prefix)
    _fila_categoria_ui("Transformadores",       vals_tr,    lab_tr,    key_prefix)

    st.markdown("---")
    # Vista consolidada del punto
    st.markdown("#### 📑 Vista consolidada del punto")
    row = _consolidado_a_fila(punto)
    st.dataframe(pd.DataFrame([row]), use_container_width=True, hide_index=True)

    # Edición rápida (restar/eliminar)
    st.markdown("##### ✂️ Editar seleccionados")
    cols = st.columns(3)
    with cols[0]:
        cat = st.selectbox("Categoría", ["Poste","Primario","Secundario","Retenidas","Conexiones a tierra","Transformadores"], key="chip_cat")
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
    # Guardar punto en df_puntos (reemplaza si existe)
    if st.button("💾 Guardar Estructura del Punto", type="primary", key="btn_guardar_estructura"):
        fila = _consolidado_a_fila(punto)
        base = st.session_state["df_puntos"]
        if not base.empty:
            base = base[base["Punto"] != punto]
        st.session_state["df_puntos"] = pd.concat([base, pd.DataFrame([fila])], ignore_index=True)
        st.success("✅ Punto guardado")

    # Tabla completa
    df_all = st.session_state["df_puntos"]
    if not df_all.empty:
        st.markdown("#### 🗂️ Puntos del proyecto")
        st.dataframe(df_all.sort_values(by="Punto"), use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Descargar CSV",
            df_all.sort_values(by="Punto").to_csv(index=False).encode("utf-8"),
            file_name="estructuras_puntos.csv",
            mime="text/csv",
            use_container_width=True,
        )

    df_final = st.session_state.get("df_puntos", pd.DataFrame(columns=COLUMNAS_BASE))
    if isinstance(df_final, pd.DataFrame) and not df_final.empty:
        return _normalizar_columnas(df_final, COLUMNAS_BASE), "UI/LISTAS"
    return None, None

# =============================================================================
# Función pública llamada por app.py
# =============================================================================

def seccion_entrada_estructuras(modo_carga: str) -> Tuple[pd.DataFrame | None, str | None]:
    """
    Devuelve siempre una tupla (df_estructuras, ruta_estructuras) según el modo:
      - "Excel"  -> carga desde file_uploader
      - "Pegar"  -> parsea texto CSV/TSV
      - otro     -> UI de Desplegables (Listas PRO, compatible con MT/BT)
    """
    modo = (modo_carga or "").strip().lower()

    if modo == "excel":
        return cargar_desde_excel()

    if modo == "pegar":
        return pegar_tabla()

    # Cualquier otro valor cae a desplegables
    return listas_desplegables()
