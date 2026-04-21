# -*- coding: utf-8 -*-
from __future__ import annotations

import streamlit as st
import pandas as pd
import re


# =========================================================
# 🔷 DEBUG GUARDAR (COMPATIBLE + MULTI-DOMINIO)
# =========================================================
def debug_guardar(*args):
    """
    MODOS:
    ✔ debug_guardar(clave, valor)
    ✔ debug_guardar(dominio, etapa, clave, valor)
    """

    if "debug_pipeline" not in st.session_state:
        st.session_state["debug_pipeline"] = {}

    dbg = st.session_state["debug_pipeline"]

    # =========================
    # MODO SIMPLE (LEGACY)
    # =========================
    if len(args) == 2:
        clave, valor = args

        try:
            dbg[clave] = valor
        except:
            dbg[clave] = str(valor)

        return

    # =========================
    # MODO PROFESIONAL
    # =========================
    if len(args) == 4:
        dominio, etapa, clave, valor = args

        if dominio not in dbg:
            dbg[dominio] = {}

        if etapa not in dbg[dominio]:
            dbg[dominio][etapa] = {}

        try:
            dbg[dominio][etapa][clave] = valor
        except:
            dbg[dominio][etapa][clave] = str(valor)

        return


# =========================================================
# 🔷 LIMPIAR DEBUG
# =========================================================
def debug_limpiar():
    st.session_state["debug_pipeline"] = {}


# =========================================================
# 🔷 BUSCAR DF AUTOMÁTICO
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
# 🔷 NORMALIZACIÓN DF
# =========================================================
def _normalizar_df(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()

    df.columns = [c.strip() for c in df.columns]

    col_est = "codigodeestructura" if "codigodeestructura" in df.columns else "Estructura"

    df[col_est] = df[col_est].astype(str).str.upper().str.strip()
    df["Punto"] = df["Punto"].astype(str).str.upper().str.strip()

    # normalizar puntos → P-01
    def fix_punto(p):
        m = re.search(r"P-(\d+)", p)
        if m:
            return f"P-{int(m.group(1)):02d}"
        return p

    df["Punto"] = df["Punto"].apply(fix_punto)

    # eliminar duplicados
    df = df.drop_duplicates(subset=["Punto", col_est])

    return df


# =========================================================
# 🔷 VISOR DEBUG (MEJORADO)
# =========================================================
def seccion_debug():

    st.title("🧠 Debug del sistema")

    debug = st.session_state.get("debug_pipeline", {})

    if debug:

        st.markdown("### 📊 Variables capturadas")

        # =========================
        # VISOR INTELIGENTE
        # =========================
        for k, v in debug.items():

            # 🔥 MODO NUEVO (DOMINIOS)
            if isinstance(v, dict) and any(isinstance(i, dict) for i in v.values()):

                st.markdown(f"# 🔷 {k}")

                for etapa, contenido in v.items():

                    st.markdown(f"## 🔹 {etapa}")

                    for sub_k, sub_v in contenido.items():

                        st.markdown(f"### {sub_k}")

                        if isinstance(sub_v, (dict, list)):
                            st.json(sub_v)
                        elif hasattr(sub_v, "head"):
                            st.dataframe(sub_v)
                        else:
                            st.write(sub_v)

            else:
                # 🔥 MODO ANTIGUO
                st.markdown(f"#### 🔹 {k}")

                if isinstance(v, (dict, list)):
                    st.json(v)
                elif hasattr(v, "head"):
                    st.dataframe(v)
                else:
                    st.write(v)

    else:
        st.info("No hay debug aún")

    # =====================================================
    # BOTÓN LIMPIAR
    # =====================================================
    if st.button("🧹 Limpiar debug"):
        debug_limpiar()
        st.success("Debug limpiado")

    # =====================================================
    # BUSCAR DF
    # =====================================================
    st.markdown("### 🔎 Vista rápida de estructuras")

    df = _buscar_df_estructuras()

    if df is None:
        st.warning("No se encontró DataFrame de estructuras")
        return

    st.success("✔ DF encontrado")
    st.write("Shape:", df.shape)
    st.dataframe(df.head(20))

    col = "codigodeestructura" if "codigodeestructura" in df.columns else "Estructura"

    # =====================================================
    # CONTEO
    # =====================================================
    st.markdown("### 🔢 Conteo por estructura")

    if "Cantidad" in df.columns:
        st.dataframe(df.groupby(col)["Cantidad"].sum().sort_values(ascending=False))
    else:
        st.dataframe(df[col].value_counts())


# =========================================================
# 🔷 DEBUG COMPLETO (ANÁLISIS)
# =========================================================
def ejecutar_debug_completo():

    st.title("🧠 DEBUG REAL DEL SISTEMA")

    df = _buscar_df_estructuras()

    if df is None:
        st.error("❌ No se encontró df_estructuras")
        st.write(list(st.session_state.keys()))
        return

    df = _normalizar_df(df)

    col = "codigodeestructura" if "codigodeestructura" in df.columns else "Estructura"

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
    st.write("Puntos únicos:", df_pc30["Punto"].nunique())
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
    # PUNTOS
    # =====================================================
    st.markdown("### 📍 Conteo por punto")

    st.dataframe(df["Punto"].value_counts().sort_index())
