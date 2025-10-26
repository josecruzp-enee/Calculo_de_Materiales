# interfaz/estructuras.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Tuple, Optional
import pandas as pd

import io
import os
import re
import time
import tempfile
from typing import Tuple, List, Dict

import pandas as pd
import streamlit as st

import pandas as pd
# otros imports que tengas

# --- Función de debug y normalización ---
def debug_y_normalizar_df(df_expandido):
    columnas_a_chequear = ["Punto", "codigodeestructura"]

    for col in columnas_a_chequear:
        for i, val in enumerate(df_expandido[col]):
            if isinstance(val, (list, tuple)):
                print(f"⚠️ Fila {i}, columna '{col}' contiene un objeto no 1D: {val}")
                df_expandido.at[i, col] = val[0] if len(val) > 0 else None
            elif val is None:
                print(f"⚠️ Fila {i}, columna '{col}' es None. Convertido a string vacío.")
                df_expandido.at[i, col] = ""
        df_expandido[col] = df_expandido[col].astype(str)

    print("✅ Debug y normalización completados. DataFrame listo para exportar.")
    print(df_expandido.head())
    return df_expandido



# =============================================================================
# Esquema base (ANCHO) que ve el usuario en la UI
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

# =============================================================================
# Utilidades de normalización / parseo
# =============================================================================
def _normalizar_columnas(df: pd.DataFrame, columnas: List[str]) -> pd.DataFrame:
    """Asegura todas las columnas requeridas en orden ANCHO y renombra variantes comunes."""
    df = df.copy()
    df = df.rename(columns={
        "Retenida": "Retenidas",
        "Aterrizaje": "Conexiones a tierra",
        "Transformador": "Transformadores",
    })
    for c in columnas:
        if c not in df.columns:
            df[c] = ""
    return df[columnas]

def _norm_code_value(s: str) -> str:
    """Limpia código de estructura: recorta y quita sufijos finales '(E)/(P)/(R)'."""
    if pd.isna(s):
        return ""
    s = str(s).strip()
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s).strip()
    return s

def _split_cell_items(cell: str) -> list[str]:
    """Separa una celda por coma, punto y coma o SALTOS DE LÍNEA (maneja comillas)."""
    if not isinstance(cell, str):
        return []
    s = cell.strip().strip('"').strip("'")
    if not s or s == "-":
        return []
    parts = re.split(r'[,;\n\r]+', s)
    return [p.strip() for p in parts if p.strip()]

def _parse_item(piece: str) -> tuple[str, int]:
    """
    Interpreta cantidad + código. Soporta:
      - '2× R-1' / '2x R-1'
      - '2 R-1'
      - '2B-I-4'  (cantidad pegada al código)
      - 'A-I-4 (E)' (cantidad implícita 1)
    """
    m = re.match(r'^(\d+)\s*[x×]\s*(.+)$', piece, flags=re.I)   # 2x CODE
    if m:
        return _norm_code_value(m.group(2)), int(m.group(1))
    m = re.match(r'^(\d+)\s+(.+)$', piece)                      # 2 CODE
    if m:
        return _norm_code_value(m.group(2)), int(m.group(1))
    m = re.match(r'^(\d+)([A-Za-z].+)$', piece)                 # 2CODE
    if m:
        return _norm_code_value(m.group(2)), int(m.group(1))
    return _norm_code_value(piece), 1

def _expand_wide_to_long(df_ancho: pd.DataFrame) -> pd.DataFrame:
    """
    ANCHO -> LARGO para el motor de reportes.
    Devuelve columnas: Punto, codigodeestructura, cantidad
    """
    df = _normalizar_columnas(df_ancho, COLUMNAS_BASE).copy()
    cat_cols = ["Poste", "Primario", "Secundario", "Retenidas", "Conexiones a tierra", "Transformadores"]
    rows = []
    for _, r in df.iterrows():
        punto = str(r.get("Punto", "")).strip()
        for col in cat_cols:
            for piece in _split_cell_items(str(r.get(col, "") or "")):
                code, qty = _parse_item(piece)
                if code:
                    rows.append({
                        "Punto": punto,
                        "codigodeestructura": code,   # EXACTO como lo exige el generador
                        "cantidad": int(qty),
                    })
    return pd.DataFrame(rows, columns=["Punto", "codigodeestructura", "cantidad"])

def _materializar_df_a_archivo(df_ancho: pd.DataFrame, etiqueta: str = "data") -> str:
    """
    Crea un .xlsx temporal con:
      • Hoja 'estructuras'       -> LARGO (Punto, codigodeestructura, cantidad)  [PRIMERA]
      • Hoja 'estructuras_ancha' -> ANCHO (para inspección en la UI)
    """
    ts = int(time.time())
    ruta = os.path.join(tempfile.gettempdir(), f"estructuras_{etiqueta}_{ts}.xlsx")

    df_ancho_norm = _normalizar_columnas(df_ancho, COLUMNAS_BASE)
    df_largo = _expand_wide_to_long(df_ancho_norm)

    try:
        writer = pd.ExcelWriter(ruta, engine="openpyxl")
    except Exception:
        writer = pd.ExcelWriter(ruta, engine="xlsxwriter")

    with writer:
        # PRIMERA hoja: la que consume el reporte
        df_largo.to_excel(writer, sheet_name="estructuras", index=False)
        # Auxiliar para ver lo que el usuario cargó/armó
        df_ancho_norm.to_excel(writer, sheet_name="estructuras_ancha", index=False)

    # Debug mínimo útil
    try:
        xls = pd.ExcelFile(ruta)
        hoja = next((s for s in xls.sheet_names if s.lower() == "estructuras"), xls.sheet_names[0])
        cols = list(pd.read_excel(xls, sheet_name=hoja, nrows=0).columns)
        st.caption("🔎 Estructuras generadas (debug)")
        st.write({"ruta": ruta, "hojas": xls.sheet_names, "columnas_estructuras": cols})
    except Exception:
        pass

    return ruta

# =============================================================================
# Carga desde Excel del usuario
# =============================================================================
def _parsear_texto_a_df(texto: str, columnas: List[str]) -> pd.DataFrame:
    """Convierte texto pegado (CSV/TSV/; o | o whitespace) a DataFrame ANCHO."""
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

def cargar_desde_excel() -> Tuple[pd.DataFrame | None, str | None]:
    archivo = st.file_uploader("Archivo de estructuras (.xlsx)", type=["xlsx"], key="upl_estructuras")
    if not archivo:
        return None, None
    try:
        xls = pd.ExcelFile(archivo)
        hoja = next((s for s in xls.sheet_names if s.strip().lower() == "estructuras"), xls.sheet_names[0])
        df_ancho = pd.read_excel(xls, sheet_name=hoja)
    except Exception as e:
        st.error(f"Error leyendo el Excel: {e}")
        return None, None

    df_ancho = _normalizar_columnas(df_ancho, COLUMNAS_BASE)
    ruta_tmp = _materializar_df_a_archivo(df_ancho, "excel")
    df_largo = _expand_wide_to_long(df_ancho)
    st.success(f"✅ Cargadas {len(df_largo)} filas (largo) desde Excel")
    return df_largo, ruta_tmp

# =============================================================================
# Pegar tabla (texto)
# =============================================================================
def pegar_tabla() -> Tuple[pd.DataFrame | None, str | None]:
    texto_pegado = st.text_area("Pega aquí tu tabla (CSV/TSV). Soporta coma y saltos de línea en celdas.", height=200, key="txt_pegar_tabla")
    if not texto_pegado:
        return None, None
    df_ancho = _parsear_texto_a_df(texto_pegado, COLUMNAS_BASE)
    if df_ancho is None or df_ancho.empty:
        st.warning("No se detectaron filas válidas en el texto.")
        return None, None
    ruta_tmp = _materializar_df_a_archivo(df_ancho, "pega")
    df_largo = _expand_wide_to_long(df_ancho)
    st.success(f"✅ Tabla pegada convertida ({len(df_largo)} filas)")
    return df_largo, ruta_tmp

# =============================================================================
# Desplegables (UI PRO)
# =============================================================================
def _cargar_opciones_catalogo() -> Dict[str, Dict[str, object]]:
    """
    Intenta cargar opciones desde modulo.desplegables.cargar_opciones().
    Estructura por categoría:
      {"valores": [cod1, cod2, ...], "etiquetas": {cod1: "cod1 – desc", ...}}
    Si no existe el módulo, retorna un fallback mínimo.
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
        # Fallback simple para no romper la UI
        return {
            "Poste": {"valores": ["PM-40 (E)", "PC-40 (E)"], "etiquetas": {}},
            "MT": {"valores": ["A-I-1 (E)", "A-II-5 (E)", "A-III-7 (E)"], "etiquetas": {}},
            "BT": {"valores": ["B-I-1 (R)", "B-II-4C (R)", "B-II-6A (R)"], "etiquetas": {}},
            "Retenidas": {"valores": ["R-1 (E)", "R-4 (D)", "R-5T (E)"], "etiquetas": {}},
            "Conexiones a tierra": {"valores": ["CT-N (P)", "CT-N (E)"], "etiquetas": {}},
            "Transformadores": {"valores": ["TD (P)", "25 kVA", "50 kVA"], "etiquetas": {}},
        }

def _pick_vals_labels(opciones: dict, prefer: list[str], fuzzy: list[str] | None = None):
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
    """UI PRO con desplegables; guarda en sesión (ANCHO) y retorna (LARGO, ruta)."""
    _ensure_df_sesion()
    _ensure_punto()
    _ensure_consolidado()

    df_actual = st.session_state["df_puntos"]
    punto = st.session_state["punto_en_edicion"]
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

    vals_poste, lab_poste = _pick_vals_labels(opciones, ["Poste"], ["poste"])
    vals_pri, lab_pri = _pick_vals_labels(opciones,
        prefer=["Primario", "Primaria", "MT", "Media Tensión", "Media Tension"],
        fuzzy=["primar", "media", "mt"]
    )
    vals_sec, lab_sec = _pick_vals_labels(opciones,
        prefer=["Secundario", "Secundaria", "BT", "Baja Tensión", "Baja Tension"],
        fuzzy=["secund", "baja", "bt"]
    )
    vals_ret, lab_ret = _pick_vals_labels(opciones, ["Retenidas"], ["reten"])
    vals_ct,  lab_ct  = _pick_vals_labels(opciones, ["Conexiones a tierra", "Tierra"], ["tierra"])
    vals_tr,  lab_tr  = _pick_vals_labels(opciones, ["Transformadores", "Transformador"], ["trafo", "transfor"])

    key_prefix = f"kp_{punto}"
    _fila_categoria_ui("Poste",                 vals_poste, lab_poste, key_prefix)
    _fila_categoria_ui("Primario",              vals_pri,   lab_pri,   key_prefix)
    _fila_categoria_ui("Secundario",            vals_sec,   lab_sec,   key_prefix)
    _fila_categoria_ui("Retenidas",             vals_ret,   lab_ret,   key_prefix)
    _fila_categoria_ui("Conexiones a tierra",   vals_ct,    lab_ct,    key_prefix)
    _fila_categoria_ui("Transformadores",       vals_tr,    lab_tr,    key_prefix)

    st.markdown("---")
    st.markdown("#### 📑 Vista consolidada del punto")
    row = _consolidado_a_fila(punto)
    st.dataframe(pd.DataFrame([row]), use_container_width=True, hide_index=True)

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
        st.download_button(
            "⬇️ Descargar CSV (ancho)",
            df_all_wide.sort_values(by="Punto").to_csv(index=False).encode("utf-8"),
            file_name="estructuras_puntos.csv",
            mime="text/csv",
            use_container_width=True,
        )

    if isinstance(df_all_wide, pd.DataFrame) and not df_all_wide.empty:
        df_all_wide = _normalizar_columnas(df_all_wide, COLUMNAS_BASE)
        ruta_tmp = _materializar_df_a_archivo(df_all_wide, "ui")
        df_largo = _expand_wide_to_long(df_all_wide)
        return df_largo, ruta_tmp

    return None, None

# =============================================================================
# Función pública: llamada por app.py
# =============================================================================
# =============================================================================
# Función pública: llamada por app.py
# =============================================================================
from typing import Tuple, Optional
import pandas as pd
import streamlit as st

# Asegúrate de que estas funciones estén definidas o importadas:
# cargar_desde_excel(), pegar_tabla(), listas_desplegables()

def seccion_entrada_estructuras(modo_carga: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Devuelve (df_estructuras_largo, ruta_estructuras_xlsx) según el modo:
      - "excel"  -> cargar desde .xlsx
      - "pegar"  -> pegar CSV/TSV en texto
      - otro     -> UI de Desplegables
    """
    modo = (modo_carga or "").strip().lower()
    if modo == "excel":
        return cargar_desde_excel()
    if modo == "pegar":
        return pegar_tabla()

    # ✅ Si no es ninguno de los anteriores → usar la UI de desplegables
    res = listas_desplegables()
    if res is None or not isinstance(res, tuple):
        return None, None

    # --- 🧩 DEBUG + LIMPIEZA ---
    try:
        if isinstance(res, tuple) and isinstance(res[0], pd.DataFrame):
            df_dbg = res[0].copy()

            # 🔧 Normalización: convertir listas/tuplas a texto plano
            for col in ["Punto", "codigodeestructura"]:
                if col in df_dbg.columns:
                    df_dbg[col] = df_dbg[col].apply(
                        lambda x: ", ".join(map(str, x)) if isinstance(x, (list, tuple, set)) else str(x)
                    )

            # Reemplazar nulos por cadenas vacías
            df_dbg = df_dbg.fillna("")

            # Mostrar vista previa en Streamlit
            st.markdown("### 🧪 DEBUG: vista previa de df_expandido (normalizado)")
            st.dataframe(df_dbg.head(10), use_container_width=True)
            st.write("**Columnas:**", list(df_dbg.columns))
            st.write("**Tipos de datos:**")
            st.write(df_dbg.dtypes)
            st.write("**Forma:**", df_dbg.shape)

            # Reasignar el DataFrame limpio al resultado
            res = (df_dbg, res[1])
    except Exception as e:
        st.error(f"⚠️ Error en debug de seccion_entrada_estructuras: {e}")

    return res

