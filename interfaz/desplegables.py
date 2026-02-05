# modulo/desplegables.py
# -*- coding: utf-8 -*-

import os
from collections import Counter
import pandas as pd
import streamlit as st
from interfaz.desplegables import debug_catalogo_excel with st.expander("🧪 Debug catálogo", expanded=True): debug_catalogo_excel() 
REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
RUTA_EXCEL = os.path.join(REPO_ROOT, "data", "Estructura_datos.xlsx")

def debug_catalogo_excel() -> dict:
    """
    Debug visual del catálogo (hoja 'indice') para encontrar por qué llegan options vacías.
    Devuelve también el dict 'opciones' por si lo querés inspeccionar.
    """
    st.subheader("🧪 DEBUG CATÁLOGO (Estructura_datos.xlsx → indice)")

    st.write("📌 RUTA_EXCEL:", RUTA_EXCEL)
    st.write("📌 Existe archivo:", os.path.exists(RUTA_EXCEL))

    try:
        xls = pd.ExcelFile(RUTA_EXCEL)
        st.write("📄 Hojas disponibles:", xls.sheet_names)
    except Exception as e:
        st.error(f"❌ No pude abrir el Excel: {e}")
        return {}

    try:
        df = pd.read_excel(RUTA_EXCEL, sheet_name="indice")
    except Exception as e:
        st.error(f"❌ No pude leer hoja 'indice': {e}")
        return {}

    st.write("📌 Columnas crudas:", list(df.columns))
    df.columns = df.columns.astype(str).str.replace("\xa0", " ").str.strip()
    st.write("📌 Columnas normalizadas:", list(df.columns))

    # detectar columnas
    clas_col = "Clasificación" if "Clasificación" in df.columns else "Clasificacion"
    cod_col  = "Código de Estructura" if "Código de Estructura" in df.columns else "Codigo de Estructura"
    desc_col = "Descripción" if "Descripción" in df.columns else "Descripcion"

    st.write("✅ Usando columnas:", {"clas": clas_col, "cod": cod_col, "desc": desc_col})

    # normalizar valores de clasificación (aquí es donde mueren muchos)
    df[clas_col] = df[clas_col].astype(str).str.replace("\xa0", " ").str.strip()
    df[cod_col]  = df[cod_col].astype(str).str.replace("\xa0", " ").str.strip()
    if desc_col in df.columns:
        df[desc_col] = df[desc_col].astype(str).str.replace("\xa0", " ").str.strip()

    st.write("🔎 Top 10 filas (clas/cod/desc):")
    st.dataframe(df[[clas_col, cod_col, desc_col]].head(10))

    st.write("🔎 Clasificaciones únicas (repr para ver espacios invisibles):")
    uniques = sorted({repr(x) for x in df[clas_col].dropna().unique().tolist()})
    st.write(uniques)

    # conteo por clasificación
    st.write("📊 Conteo por clasificación:")
    conteo = df[clas_col].value_counts(dropna=False)
    st.dataframe(conteo)

    # construir opciones y reportar tamaños
    mapping = {
        "Poste": "Poste",
        "Primaria": "Primario",
        "Secundaria": "Secundario",
        "Retenidas": "Retenidas",
        "Conexiones a tierra": "Conexiones a tierra",
        "Protección": "Protección",
        "Proteccion": "Protección",
        "Transformadores": "Transformadores",
        "Luminarias": "Luminarias",
        "Luminaria": "Luminarias",  # 👈 por si tu Excel usa "Luminaria"
    }

    opciones = {}
    for clasificacion in df[clas_col].dropna().astype(str).unique():
        clasificacion = str(clasificacion).replace("\xa0", " ").strip()
        subset = df[df[clas_col] == clasificacion]

        codigos = subset[cod_col].dropna().astype(str).str.strip().tolist()
        etiquetas = {
            str(row[cod_col]).strip(): f"{str(row[cod_col]).strip()} – {str(row[desc_col]).strip() if pd.notna(row[desc_col]) else ''}"
            for _, row in subset.iterrows()
            if pd.notna(row[cod_col])
        }

        kk = mapping.get(clasificacion, clasificacion)
        opciones[kk] = {"valores": codigos, "etiquetas": etiquetas}

    st.write("✅ Keys finales en opciones:", list(opciones.keys()))
    st.write("✅ Tamaños por key:")
    st.dataframe(pd.DataFrame(
        [{"key": k, "n": len(v.get("valores", []))} for k, v in opciones.items()]
    ))

    # alertas rápidas
    esperadas = ["Poste", "Primario", "Secundario", "Retenidas", "Conexiones a tierra", "Protección", "Transformadores", "Luminarias"]
    faltan = [k for k in esperadas if k not in opciones or len(opciones[k].get("valores", [])) == 0]
    if faltan:
        st.error(f"❌ Categorías faltantes o vacías: {faltan}")
    else:
        st.success("✅ Catálogo OK: todas las categorías tienen opciones.")

    return opciones


# ========== Cargar catálogo desde "indice" ==========
def cargar_opciones():
    import os
    import pandas as pd
    import streamlit as st

    # =========================
    # DEBUG CATÁLOGO (EXCEL)
    # =========================
    st.write("🧪 DEBUG CATÁLOGO")
    st.write("RUTA_EXCEL:", RUTA_EXCEL)
    st.write("EXISTE:", os.path.exists(RUTA_EXCEL))

    if os.path.exists(RUTA_EXCEL):
        try:
            xls = pd.ExcelFile(RUTA_EXCEL)
            st.write("HOJAS DISPONIBLES:", xls.sheet_names)

            # intenta encontrar la hoja "indice" aunque tenga mayúsculas/acentos/espacios
            sheets_norm = {str(s).strip().lower(): s for s in xls.sheet_names}
            hoja_indice = sheets_norm.get("indice") or sheets_norm.get("índice") or sheets_norm.get("indice ")  # por si acaso
            st.write("HOJA INDICE detectada:", hoja_indice)

            if hoja_indice:
                df0 = pd.read_excel(xls, sheet_name=hoja_indice, nrows=20)
                df0.columns = [str(c).strip() for c in df0.columns]
                st.write("COLUMNAS (indice):", df0.columns.tolist())
                st.write("MUESTRA (primeras filas):")
                st.dataframe(df0)
            else:
                st.error("❌ No encontré una hoja llamada 'indice' (o 'Índice'). Revisá el nombre exacto.")
        except Exception as e:
            st.error(f"❌ Error abriendo el Excel en RUTA_EXCEL: {e}")
            st.stop()
    else:
        st.error("❌ El archivo NO existe en esa ruta. Revisá nombre exacto y mayúsculas/minúsculas en /data.")
        st.stop()

    # =========================
    # CARGA REAL (tu lógica)
    # =========================
    # usa el nombre detectado de la hoja para evitar fallos por acentos/mayúsculas
    df = pd.read_excel(RUTA_EXCEL, sheet_name=hoja_indice)
    df.columns = df.columns.str.strip()

    clas_col = "Clasificación" if "Clasificación" in df.columns else "Clasificacion"
    cod_col  = "Código de Estructura" if "Código de Estructura" in df.columns else "Codigo de Estructura"
    desc_col = "Descripción" if "Descripción" in df.columns else "Descripcion"

    st.write("DEBUG clas_col:", clas_col)
    st.write("DEBUG cod_col:", cod_col)
    st.write("DEBUG desc_col:", desc_col)

    # valores únicos de clasificación (para ver si viene con espacios raros)
    try:
        unicos = df[clas_col].dropna().astype(str).unique().tolist()
        st.write("CLASIFICACIONES ÚNICAS (raw):", unicos[:40])
        # también una versión normalizada
        unicos_norm = [str(x).replace("\xa0", " ").strip() for x in unicos]
        st.write("CLASIFICACIONES ÚNICAS (norm):", unicos_norm[:40])
    except Exception as e:
        st.error(f"❌ No pude leer columna de clasificación: {e}")

    opciones = {}
    for clasificacion in df[clas_col].dropna().astype(str).unique():
        clasificacion = str(clasificacion).replace("\xa0", " ").strip()
        subset = df[df[clas_col].astype(str).apply(lambda x: str(x).replace("\xa0"," ").strip()) == clasificacion]

        codigos = subset[cod_col].dropna().astype(str).str.strip().tolist()

        etiquetas = {
            str(row[cod_col]).strip(): f"{str(row[cod_col]).strip()} – {str(row[desc_col]).strip() if pd.notna(row[desc_col]) else ''}"
            for _, row in subset.iterrows()
            if pd.notna(row[cod_col])
        }

        opciones[clasificacion] = {"valores": codigos, "etiquetas": etiquetas}

    mapping = {
        "Poste": "Poste",
        "Primaria": "Primario",
        "Secundaria": "Secundario",
        "Retenidas": "Retenidas",
        "Conexiones a tierra": "Conexiones a tierra",
        "Protección": "Protección",
        "Proteccion": "Protección",
        "Transformadores": "Transformadores",
        "Luminarias": "Luminarias",
        "Luminaria": "Luminarias",  # 👈 por si viene singular
    }

    normalizado = {}
    for k, v in opciones.items():
        kk = mapping.get(str(k).replace("\xa0"," ").strip(), str(k).replace("\xa0"," ").strip())
        normalizado[kk] = v

    # DEBUG FINAL: conteo por categoría ya normalizada
    st.write("✅ CATEGORÍAS NORMALIZADAS:", list(normalizado.keys()))
    for cat in ["Poste", "Primario", "Secundario", "Retenidas", "Conexiones a tierra", "Protección", "Transformadores", "Luminarias"]:
        n = len(normalizado.get(cat, {}).get("valores", []) or [])
        st.write(f"CAT {cat}: {n} opciones")

    return normalizado



# ========== Helpers de parseo (2x R-1  <->  Counter) ==========
def _parse_str_to_counter(s: str) -> Counter:
    if not s:
        return Counter()
    s = s.replace("+", ",")
    parts = [p.strip() for p in s.split(",") if p.strip()]
    c = Counter()
    for p in parts:
        low = p.lower()
        if "x" in low:
            try:
                n, cod = low.split("x", 1)
                n = int(n.strip())
                cod = cod.strip().upper()
                if cod:
                    c[cod] += max(1, n)
                continue
            except Exception:
                pass
        c[p.upper()] += 1
    return c


def _counter_to_str(c: Counter) -> str:
    if not c:
        return ""
    partes = []
    for cod, n in c.items():
        partes.append(f"{n}x {cod}" if n > 1 else cod)
    return " , ".join(partes)


# ========== UI: picker con cantidad (bonito y compacto) ==========
def _scoped_css_once():
    if st.session_state.get("_xpicker_css", False):
        return
    st.session_state["_xpicker_css"] = True
    st.markdown(
        """
        <style>
        /* Estilos SOLO dentro de .xpicker para no tocar tu tema global */
        .xpicker .count-pill{
            display:inline-block; min-width:28px; padding:2px 8px;
            border-radius:999px; text-align:center; font-weight:600;
            background:#f1f1f1; border:1px solid #e6e6e6;
        }
        .xpicker .row{
            padding:6px 8px; border:1px solid #eee; border-radius:10px;
            margin-bottom:6px; background:rgba(0,0,0,0.01);
        }
        .xpicker .stButton>button{
            padding:4px 10px; border-radius:10px;
        }
        .xpicker .muted{ color:#666; font-size:12px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _short(label: str, maxlen: int = 52) -> str:
    return label if len(label) <= maxlen else label[:maxlen - 1] + "…"


def _render_lista(contador: Counter, datos: dict, state_key: str):
    """Lista bonita con código, descripción corta, cantidad (píldora) y acciones."""
    if not contador:
        return
    st.caption("Seleccionado:")

    for cod, n in sorted(contador.items()):
        col1, col2, col3, col4 = st.columns([7, 2, 1, 1])
        with col1:
            desc = datos.get("etiquetas", {}).get(cod, cod)
            st.markdown(
                f"<div class='row'><strong>{cod}</strong> – "
                f"<span class='muted'>{_short(desc)}</span></div>",
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(f"<div class='count-pill'>× {n}</div>", unsafe_allow_html=True)
        with col3:
            if st.button("−", key=f"{state_key}_menos_{cod}", help="Quitar 1"):
                contador[cod] -= 1
                if contador[cod] <= 0:
                    del contador[cod]
                st.rerun()
        with col4:
            if st.button("🗑️", key=f"{state_key}_del_{cod}", help="Eliminar"):
                del contador[cod]
                st.rerun()


def _picker_con_cantidad(label: str, datos: dict, state_key: str, valores_previos: str = "") -> Counter:
    """
    Línea compacta: Select | Cantidad | ➕ Agregar
    + lista seleccionada con píldoras y acciones.
    """
    if not datos or not datos.get("valores"):
        st.info(f"No hay opciones para {label}.")
        return Counter()

    _scoped_css_once()

    # Estado inicial (si vienes de "Editar Punto")
    if state_key not in st.session_state:
        st.session_state[state_key] = _parse_str_to_counter(valores_previos)

    contador: Counter = st.session_state[state_key]

    # Picker compacto
    cols = st.columns([6, 2, 2])
    with cols[0]:
        codigo = st.selectbox(
            label,
            options=datos["valores"],
            format_func=lambda x: datos.get("etiquetas", {}).get(x, x),
            key=f"{state_key}_sel",
        )
    with cols[1]:
        qty = st.number_input(
            "Cantidad",
            min_value=1, value=1, step=1,
            key=f"{state_key}_qty",
            label_visibility="collapsed",
        )
    with cols[2]:
        if st.button("➕ Agregar", key=f"{state_key}_add", type="primary"):
            contador[str(codigo).strip().upper()] += int(qty)

    _render_lista(contador, datos, state_key)

    st.session_state[state_key] = contador
    return contador


# ========== Componente principal que usa interfaz/estructuras.py ==========
def crear_desplegables(opciones):
    """
    Devuelve un dict igual al que ya guardas en df_puntos:
      {'Poste': '2x PC-40', 'Primario': 'A-I-5', ...}
    """
    with st.container():  # scope para el CSS local
        st.markdown("<div class='xpicker'>", unsafe_allow_html=True)

        seleccion = {}
        df_actual = st.session_state.get("df_puntos", pd.DataFrame())
        punto_actual = st.session_state.get("punto_en_edicion")

        # Valores previos si se está editando
        valores_previos = {}
        if (not df_actual.empty) and (punto_actual in df_actual.get("Punto", pd.Series(dtype=str)).values):
            fila = df_actual[df_actual["Punto"] == punto_actual].iloc[0].to_dict()
            valores_previos = {k: v for k, v in fila.items() if k != "Punto"}

        # --- Mezclar catálogo: Conexiones a tierra + Protección ---
        cat_tierra = opciones.get("Conexiones a tierra", {"valores": [], "etiquetas": {}})
        cat_prot   = opciones.get("Protección", {"valores": [], "etiquetas": {}})

        # Merge sin duplicados, preservando etiquetas
        valores_mix = []
        vistos = set()
        for v in (cat_tierra.get("valores", []) + cat_prot.get("valores", [])):
            vv = str(v).strip()
            if vv and vv not in vistos:
                vistos.add(vv)
                valores_mix.append(vv)

        etiquetas_mix = {}
        etiquetas_mix.update(cat_tierra.get("etiquetas", {}) or {})
        etiquetas_mix.update(cat_prot.get("etiquetas", {}) or {})

        cat_tierra_prot = {"valores": valores_mix, "etiquetas": etiquetas_mix}

        # Estructura en dos columnas (como tu layout)
        col_izq, col_der = st.columns(2)

        with col_izq:
            c_poste = _picker_con_cantidad(
                "Poste", opciones.get("Poste"), "cnt_poste",
                valores_previos.get("Poste", "")
            )
            c_sec = _picker_con_cantidad(
                "Secundario", opciones.get("Secundario"), "cnt_sec",
                valores_previos.get("Secundario", "")
            )

            c_tierra = _picker_con_cantidad(
                "Conexiones a tierra / Protección",
                cat_tierra_prot,
                "cnt_tierra_prot",  # 👈 antes era "cnt_tierra"
                valores_previos.get("Conexiones a tierra", "")
            )

        with col_der:
            c_pri = _picker_con_cantidad(
                "Primario", opciones.get("Primario"), "cnt_pri",
                valores_previos.get("Primario", "")
            )
            c_ret = _picker_con_cantidad(
                "Retenidas", opciones.get("Retenidas"), "cnt_ret",
                valores_previos.get("Retenidas", "")
            )
            c_trf = _picker_con_cantidad(
                "Transformadores", opciones.get("Transformadores"), "cnt_trf",
                valores_previos.get("Transformadores", "")
            )

            c_lum = _picker_con_cantidad(
                "Luminarias", opciones.get("Luminarias"), "cnt_lum",
                valores_previos.get("Luminarias", "")
            )

        # Salida final en el formato que ya consume tu app
        seleccion["Poste"] = _counter_to_str(c_poste)
        seleccion["Primario"] = _counter_to_str(c_pri)
        seleccion["Secundario"] = _counter_to_str(c_sec)
        seleccion["Retenidas"] = _counter_to_str(c_ret)
        seleccion["Conexiones a tierra"] = _counter_to_str(c_tierra)
        seleccion["Transformadores"] = _counter_to_str(c_trf)
        seleccion["Luminarias"] = _counter_to_str(c_lum)

        st.markdown("</div>", unsafe_allow_html=True)

    return seleccion





