# -*- coding: utf-8 -*-
from __future__ import annotations

import streamlit as st
import pandas as pd
import re

def debug_guardar(clave, valor):
    import streamlit as st

    if "debug_pipeline" not in st.session_state:
        st.session_state["debug_pipeline"] = {}

    try:
        st.session_state["debug_pipeline"][clave] = valor
    except:
        st.session_state["debug_pipeline"][clave] = str(valor) 
# =========================================================
# 🔷 BUSCAR DF AUTOMÁTICO (NO DEPENDE DEL ORQUESTADOR)
# =========================================================
def _buscar_df_estructuras():

    for key, val in st.session_state.items():
        if isinstance(val, pd.DataFrame):
            cols = [c.lower() for c in val.columns]

            if "punto" in cols and (
                "codigodeestructura" in cols or "estructura" in cols
            ):
                return val

    return None


# =========================================================
# 🔷 NORMALIZACIÓN
# =========================================================
def _normalizar_df(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()

    # limpiar
    df.columns = [c.strip() for c in df.columns]

    col_est = "codigodeestructura" if "codigodeestructura" in df.columns else "Estructura"

    df[col_est] = df[col_est].astype(str).str.upper().str.strip()
    df["Punto"] = df["Punto"].astype(str).str.upper().str.strip()

    # normalizar puntos
    def fix_punto(p):
        m = re.search(r"P-(\d+)", p)
        if m:
            return f"P-{int(m.group(1)):02d}"
        return p

    df["Punto"] = df["Punto"].apply(fix_punto)

    # eliminar duplicados reales
    df = df.drop_duplicates(subset=["Punto", col_est])

    return df

# =========================================================
# 🔷 DEBUG BÁSICO (SIN DEPENDENCIAS)
# =========================================================
def seccion_debug():

    st.title("🧠 Debug del sistema (modo estable)")

    debug = st.session_state.get("debug_pipeline", {})

    if debug:
        st.markdown("### 📊 Variables capturadas")
        for k, v in debug.items():
            st.markdown(f"#### 🔹 {k}")
            try:
                st.json(v)
            except:
                st.write(v)
    else:
        st.info("No hay debug aún")

    # Intentar mostrar cualquier DataFrame de estructuras sin romper nada
    st.markdown("### 🔎 Vista rápida de estructuras")

    df = None
    for val in st.session_state.values():
        if isinstance(val, pd.DataFrame) and "Punto" in val.columns:
            df = val
            break

    if df is None:
        st.warning("No se encontró DataFrame de estructuras")
        return

    st.success("✔ DF encontrado")
    st.write("Shape:", df.shape)
    st.dataframe(df.head(20))

    col = "codigodeestructura" if "codigodeestructura" in df.columns else "Estructura"

    st.markdown("### 🔢 Conteo por estructura")
    if "Cantidad" in df.columns:
        st.dataframe(df.groupby(col)["Cantidad"].sum().sort_values(ascending=False))
    else:
        st.dataframe(df[col].value_counts()) 
# =========================================================
# 🔷 DEBUG PRINCIPAL
# =========================================================
def ejecutar_debug_completo():

    st.title("🧠 DEBUG REAL DEL SISTEMA")

    # =====================================================
    # BUSCAR DF
    # =====================================================
    df = _buscar_df_estructuras()

    if df is None:
        st.error("❌ No se encontró df_estructuras en session_state")
        st.write(list(st.session_state.keys()))
        return

    # =====================================================
    # NORMALIZAR
    # =====================================================
    df = _normalizar_df(df)

    # detectar columna
    col = "codigodeestructura" if "codigodeestructura" in df.columns else "Estructura"

    # =====================================================
    # INFO GENERAL
    # =====================================================
    st.success("✔ DF detectado correctamente")
    st.write("Shape:", df.shape)
    st.write("Columnas:", list(df.columns))

    st.markdown("### 📊 Preview")
    st.dataframe(df.head(30), use_container_width=True)

    # =====================================================
    # CONTEO
    # =====================================================
    st.markdown("### 🔢 Conteo por estructura")

    if "Cantidad" in df.columns:
        conteo = df.groupby(col)["Cantidad"].sum().sort_values(ascending=False)
    else:
        conteo = df[col].value_counts()

    st.dataframe(conteo)

    # =====================================================
    # VALIDACIÓN PC-30
    # =====================================================
    st.markdown("### ⚠️ Validación PC-30")

    df_pc30 = df[df[col].str.contains("PC-30", na=False)]

    st.write("Total registros PC-30:", len(df_pc30))
    st.write("Puntos únicos con PC-30:", df_pc30["Punto"].nunique())
    st.write("Lista de puntos:", sorted(df_pc30["Punto"].unique()))

    # =====================================================
    # DUPLICADOS
    # =====================================================
    st.markdown("### 🧨 Duplicados")

    dup = df[df.duplicated(subset=["Punto", col], keep=False)]

    if dup.empty:
        st.success("✔ No hay duplicados")
    else:
        st.error("❌ DUPLICADOS DETECTADOS")
        st.dataframe(dup)

    # =====================================================
    # CONTEO POR PUNTO
    # =====================================================
    st.markdown("### 📍 Conteo por punto")

    st.dataframe(df["Punto"].value_counts().sort_index())
