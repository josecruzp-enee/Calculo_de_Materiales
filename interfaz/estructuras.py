# interfaz/estructuras.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import os
import time
import tempfile
from typing import Tuple, List, Dict

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

import re

def _parse_items_cell(cell: str):
    """
    Convierte '2× R-1, A-I-5 (E)' -> [('R-1',2),('A-I-5',1)]
    Acepta 'x' o '×' y quita sufijos entre paréntesis (E)/(P)/(R).
    """
    if not isinstance(cell, str):
        return []
    s = cell.strip()
    if not s or s == "-":
        return []
    items = []
    for piece in [p.strip() for p in s.split(",") if p.strip()]:
        m = re.match(r"^(\d+)\s*[x×]\s*(.+)$", piece, flags=re.I)
        qty = int(m.group(1)) if m else 1
        code = (m.group(2) if m else piece).strip()
        # quitar sufijo entre paréntesis final, ej. 'A-I-4 (E)' -> 'A-I-4'
        code = re.sub(r"\s*\([^)]*\)\s*$", "", code).strip()
        if code:
            items.append((code, qty))
    return items

def _expand_wide_to_long(df_ancho: pd.DataFrame) -> pd.DataFrame:
    """
    De la tabla ancha (Punto, Poste, Primario, Secundario, Retenidas, Conexiones a tierra, Transformadores)
    genera filas con columnas: Punto, codigodeestructura, cantidad, categoria.
    """
    cat_cols = [
        ("Poste", "Poste"),
        ("Primario", "Primario"),             # MT
        ("Secundario", "Secundario"),         # BT
        ("Retenidas", "Retenidas"),
        ("Conexiones a tierra", "Conexiones a tierra"),
        ("Transformadores", "Transformadores"),
    ]
    rows = []
    for _, r in df_ancho.iterrows():
        punto = str(r.get("Punto", "")).strip()
        for col, cat in cat_cols:
            cell = str(r.get(col, "") or "").strip()
            for code, qty in _parse_items_cell(cell):
                rows.append({
                    "Punto": punto,
                    "codigodeestructura": code,  # en minúsculas todo junto (lo que pide el reporte)
                    "cantidad": int(qty),
                    "categoria": cat,
                })
    return pd.DataFrame(rows, columns=["Punto", "codigodeestructura", "cantidad", "categoria"])

def _normalizar_columnas(df: pd.DataFrame, columnas: List[str]) -> pd.DataFrame:
    """Asegura todas las columnas requeridas y ordena como espera la app."""
    df = df.copy()
    # Renombres comunes desde archivos del usuario
    df = df.rename(columns={
        "Retenida": "Retenidas",
        "Aterrizaje": "Conexiones a tierra",
        "Transformador": "Transformadores",
    })
    for c in columnas:
        if c not in df.columns:
            df[c] = ""
    # Mantener orden
    return df[columnas]

def _parsear_texto_a_df(texto: str, columnas: List[str]) -> pd.DataFrame:
    """Convierte texto pegado (CSV/TSV/; o | o whitespace) a DataFrame ancho."""
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

def _materializar_df_a_archivo(df: pd.DataFrame, etiqueta: str = "data") -> str:
    """
    Escribe un .xlsx temporal con:
      - Hoja 'estructuras'      -> formato LARGO con columnas: Punto, codigodeestructura, cantidad, categoria
      - Hoja 'estructuras_ancha'-> formato ANCHO para revisión en la UI
    """
    ts = int(time.time())
    tmpdir = tempfile.gettempdir()
    ruta = os.path.join(tmpdir, f"estructuras_{etiqueta}_{ts}.xlsx")

    df_ancho = _normalizar_columnas(df, COLUMNAS_BASE)
    df_largo = _expand_wide_to_long(df_ancho)

    # Escritor Excel
    try:
        writer = pd.ExcelWriter(ruta, engine="openpyxl")
    except Exception:
        try:
            writer = pd.ExcelWriter(ruta, engine="xlsxwriter")
        except Exception as e:
            st.error("No se pudo crear el Excel temporal. Instala 'openpyxl' o 'xlsxwriter'.")
            raise e

    with writer:
        # Esta es la hoja que lee tu motor de reportes
        df_largo.to_excel(writer, sheet_name="estructuras", index=False)
        # Hoja auxiliar para que tú veas el resumen ancho
        df_ancho.to_excel(writer, sheet_name="estructuras_ancha", index=False)

    return ruta


# =============================================================================
# Modo: Excel
# =============================================================================

def cargar_desde_excel() -> Tuple[pd.DataFrame | None, str | None]:
    archivo = st.file_uploader("Archivo de estructuras (.xlsx)", type=["xlsx"], key="upl_estructuras")
    if not archivo:
        return None, None
    nombre = getattr(archivo, "name", "estructura_lista.xlsx")
    try:
        # Si el archivo ya tiene hoja 'estructuras', úsala; si no, lee la primera y normaliza
        xls = pd.ExcelFile(archivo)
        hoja = None
        for s in xls.sheet_names:
            if s.strip().lower() == "estructuras":
                hoja = s
                break
        df = pd.read_excel(xls, sheet_name=hoja or xls.sheet_names[0])
    except Exception as e:
        st.error(f"Error leyendo el Excel: {e}")
        return None, None

    df = _normalizar_columnas(df, COLUMNAS_BASE)
    ruta_tmp = _materializar_df_a_archivo(df, "excel")
    st.success(f"✅ Cargadas {len(df)} filas desde {nombre}")
    return df, ruta_tmp

# =============================================================================
# Modo: Pegar tabla (CSV/TSV)
# =============================================================================

def pegar_tabla() -> Tuple[pd.DataFrame | None, str | None]:
    texto_pegado = st.text_area("Pega aquí tu tabla (CSV/TSV)", height=200, key="txt_pegar_tabla")
    if not texto_pegado:
        return None, None
    df = _parsear_texto_a_df(texto_pegado, COLUMNAS_BASE)
    if df is None or df.empty:
        st.warning("No se detectaron filas válidas en el texto.")
        return None, None
    ruta_tmp = _materializar_df_a_archivo(df, "pega")
    st.success(f"✅ Tabla cargada con {len(df)} filas")
    return df, ruta_tmp

# =============================================================================
# Modo: Desplegables (Listas PRO) con MT/BT
# =============================================================================

def _cargar_opciones_catalogo() -> Dict[str, Dict[str, object]]:
    """
    Intenta cargar opciones desde modulo.desplegables.cargar_opciones().
    Estructura por categoría:
      {"valores": [cod1, cod2, ...], "etiquetas": {cod1: "cod1 – desc", ...}}
    Si no existe el módulo, retorna un fallback mínimo (para que la UI no se rompa).
    """
    try:
        from modulo.desplegables import cargar_opciones  # type: ignore
        opciones = cargar_opciones()
        # Normalización suave de claves esperadas
        for key in ["Poste", "Primaria", "Primario", "Secundaria", "Secundario", "MT", "BT",
                    "Retenidas", "Conexiones a tierra", "Transformadores", "Transformador"]:
            opciones.setdefault(key, {"valores": [], "etiquetas": {}})
            opciones[key].setdefault("valores", [])
            opciones[key].setdefault("etiquetas", {})
        return opciones
    except Exception:
        # Fallback simple
        return {
            "Poste": {"valores": ["PC-40 (E)", "PM-35 (E)"], "etiquetas": {
                "PC-40 (E)": "PC-40 (E) – Poste de Concreto de 40 Pies.",
                "PM-35 (E)": "PM-35 (E) – Poste de Madera de 35 Pies.",
            }},
            "MT": {"valores": ["A-I-1 (E)", "A-II-5 (E)", "A-III-7 (E)"], "etiquetas": {}},
            "BT": {"valores": ["B-I-1 (R)", "B-II-1 (R)", "B-II-4C (R)"], "etiquetas": {}},
            "Retenidas": {"valores": ["R-1 (E)", "R-4 (E)", "R-5T (E)"], "etiquetas": {}},
            "Conexiones a tierra": {"valores": ["CT-N (P)", "CT-N (E)"], "etiquetas": {}},
            "Transformadores": {"valores": ["TD (P)", "25 kVA", "37.5 kVA", "50 kVA"], "etiquetas": {}},
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
    """Devuelve una fila ancho (como tu Excel de ejemplo)."""
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
    Consolida por Punto y guarda en st.session_state["df_puntos"] en formato ancho.
    Devuelve (df, ruta_tmp_xlsx) cuando hay datos.
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

    # MT/BT y variantes + Primario/Secundario (robusto a nombres)
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
    # Vista consolidada del punto (formato ancho)
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

    # Tabla completa (ancha)
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
        df_final = _normalizar_columnas(df_final, COLUMNAS_BASE)
        ruta_tmp = _materializar_df_a_archivo(df_final, "ui")
        return df_final, ruta_tmp
    return None, None

# =============================================================================
# Función pública llamada por app.py
# =============================================================================

def seccion_entrada_estructuras(modo_carga: str) -> Tuple[pd.DataFrame | None, str | None]:
    """
    Devuelve siempre una tupla (df_estructuras, ruta_estructuras) según el modo:
      - "excel"  -> carga desde file_uploader y materializa a archivo temporal (hoja 'estructuras')
      - "pegar"  -> parsea texto CSV/TSV y materializa a archivo temporal (hoja 'estructuras')
      - otro     -> UI de Desplegables (MT/BT) y materializa a archivo temporal (hoja 'estructuras')
    """
    modo = (modo_carga or "").strip().lower()

    if modo == "excel":
        return cargar_desde_excel()

    if modo == "pegar":
        return pegar_tabla()

    # Cualquier otro valor cae a desplegables
    return listas_desplegables()
