# -*- coding: utf-8 -*-
from __future__ import annotations

import streamlit as st
import pandas as pd


# =========================================================
# 🔷 STORAGE GLOBAL DEBUG
# =========================================================
def debug_guardar(clave: str, valor):

    if "debug_pipeline" not in st.session_state:
        st.session_state["debug_pipeline"] = {}

    try:
        st.session_state["debug_pipeline"][clave] = valor
    except Exception:
        st.session_state["debug_pipeline"][clave] = str(valor)


# =========================================================
# 🔷 DEBUG ESTRUCTURADO
# =========================================================
def debug_step(nombre: str, data):

    debug_guardar(nombre, {
        "tipo": type(data).__name__,
        "shape": getattr(data, "shape", None),
        "preview": str(data)[:500]
    })


# =========================================================
# 🔷 ESTADO VISUAL
# =========================================================
def _estado(ok):
    return "🟢" if ok else "🔴"


# =========================================================
# 🔷 PIPELINE RUNTIME REAL
# =========================================================
def _pipeline_runtime():

    df = st.session_state.get("df_estructuras")
    resultado = st.session_state.get("resultado_calculo")

    return [
        ("UI", True),

        ("Entradas",
         isinstance(df, pd.DataFrame) and not df.empty),

        ("Normalización",
         isinstance(df, pd.DataFrame)
         and "codigodeestructura" in df.columns
         and df["codigodeestructura"].notna().any()),

        ("Materiales",
         resultado is not None
         and hasattr(resultado, "df_materiales")),

        ("Exportación", resultado is not None),
        ("PDF", resultado is not None),
    ]


# =========================================================
# 🔷 RENDER PIPELINE
# =========================================================
def _render_pipeline_runtime():

    st.markdown("### 🧠 Pipeline en tiempo real")

    pasos = _pipeline_runtime()

    for nombre, ok in pasos:

        st.write(f"{_estado(ok)} {nombre}")

        if not ok:
            st.error(f"⚠️ Falla en: {nombre}")
            break


# =========================================================
# 🔷 RENDER VALORES DEBUG
# =========================================================
def _render_valor_debug(valor):

    # =====================================================
    # DATAFRAME DIRECTO
    # =====================================================
    if isinstance(valor, pd.DataFrame):
        st.caption(f"Filas: {len(valor)} | Columnas: {list(valor.columns)}")
        st.dataframe(valor, use_container_width=True)

    # =====================================================
    # DICT (CLAVE: NO convertir todo a string)
    # =====================================================
    elif isinstance(valor, dict):

        # Mostrar JSON limpio pero SIN romper estructuras
        try:
            st.json({
                k: v if not isinstance(v, pd.DataFrame) else f"<<DataFrame {v.shape}>>"
                for k, v in valor.items()
            })
        except:
            st.write(valor)

        # 🔥 DETECTAR DATAFRAMES INTERNOS
        for k, v in valor.items():
            if isinstance(v, pd.DataFrame):
                st.markdown(f"📊 DataFrame interno: `{k}`")
                st.caption(f"Filas: {len(v)} | Columnas: {list(v.columns)}")
                st.dataframe(v, use_container_width=True)

    # =====================================================
    # OBJETO (dataclass / class)
    # =====================================================
    elif hasattr(valor, "__dict__"):
        try:
            contenido = vars(valor)

            st.json({
                k: v if not isinstance(v, pd.DataFrame) else f"<<DataFrame {v.shape}>>"
                for k, v in contenido.items()
            })

            for k, v in contenido.items():
                if isinstance(v, pd.DataFrame):
                    st.markdown(f"📊 DataFrame interno: `{k}`")
                    st.dataframe(v, use_container_width=True)

        except:
            st.write(valor)

    # =====================================================
    # OTROS
    # =====================================================
    else:
        st.write(valor)
# =========================================================
# 🔷 AUDITORÍA ESTRUCTURAS
# =========================================================
def _auditar_estructuras():

    st.markdown("### 🔍 Auditoría de estructuras")

    df = st.session_state.get("df_estructuras")

    if df is None:
        st.error("df_estructuras = None")
        return

    st.write("Shape:", df.shape)
    st.write("Columnas:", list(df.columns))
    st.dataframe(df.head(10))

    col = None
    if "codigodeestructura" in df.columns:
        col = "codigodeestructura"
    elif "Estructura" in df.columns:
        col = "Estructura"

    if col:
        st.markdown("### 🔎 Valores únicos")
        st.write(sorted(df[col].dropna().unique())[:50])


# =========================================================
# 🔷 DEBUG MATERIAL PROFUNDO
# =========================================================
def _debug_materiales_profundo():

    st.markdown("### 🔬 Trazabilidad de materiales")

    hojas = st.session_state.get("hojas_base")
    df = st.session_state.get("df_estructuras")
    tension = st.session_state.get("tension")

    if hojas is None:
        st.error("❌ No hay hojas_base")
        return

    if df is None or df.empty:
        st.error("❌ No hay estructuras")
        return

    col = "codigodeestructura" if "codigodeestructura" in df.columns else "Estructura"

    estructuras = sorted(df[col].dropna().unique())

    st.write("Total estructuras:", len(estructuras))

    for est in estructuras:

        with st.expander(f"🔎 {est}"):

            df_est = hojas.get(est)

            if df_est is None:
                st.error("❌ NO EXISTE EN BASE")
                continue

            st.success("✔ Hoja encontrada")

            # buscar tensión
            col_tension = None

            for c in df_est.columns:
                try:
                    val = float(str(c).replace(",", "."))
                    if abs(val - float(tension)) < 0.1:
                        col_tension = c
                        break
                except:
                    continue

            if col_tension is None:
                st.error(f"❌ No tiene tensión {tension}")
                continue

            df_est[col_tension] = pd.to_numeric(df_est[col_tension], errors="coerce").fillna(0)

            df_filtrado = df_est[
                (df_est[col_tension] > 0)
                & df_est["MATERIALES"].notna()
            ]

            if df_filtrado.empty:
                st.error("❌ SIN MATERIALES")
            else:
                st.success(f"✔ {len(df_filtrado)} materiales")
                st.dataframe(df_filtrado.head(10))


# =========================================================
# 🔷 DEBUG PRINCIPAL
# =========================================================
def seccion_debug():

    st.title("🧠 Debug del sistema")

    debug = st.session_state.get("debug_pipeline", {})

    if debug:
        st.markdown("### 📊 Variables capturadas")

        for k, v in debug.items():
            st.markdown(f"#### 🔹 {k}")
            _render_valor_debug(v)
    else:
        st.info("No hay debug aún")

    # ======================================================
    # Auditoría
    # ======================================================
    _auditar_estructuras()

    # ======================================================
    # Conteo correcto (FIX)
    # ======================================================
    df = st.session_state.get("df_estructuras")

    if df is not None and not df.empty:

        col = "codigodeestructura" if "codigodeestructura" in df.columns else "Estructura"

        st.markdown("### 🔢 Conteo por estructura")

        st.dataframe(
            df.groupby(col)["cantidad"]
            .sum()
            .sort_values(ascending=False)
        )

    # ======================================================
    # Pipeline
    # ======================================================
    _render_pipeline_runtime()

    # ======================================================
    # Session completa
    # ======================================================
    with st.expander("🔍 session_state completo"):
        st.json({k: str(v)[:200] for k, v in st.session_state.items()})
