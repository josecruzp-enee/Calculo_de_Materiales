# -*- coding: utf-8 -*-
from __future__ import annotations

import streamlit as st
import pandas as pd
import re


# =========================================================
# 🔷 GUARDAR DF GLOBAL (LLAMAR DESDE ORQUESTADOR)
# =========================================================
def guardar_df_estructuras(df: pd.DataFrame):
    if df is not None and not df.empty:
        st.session_state["df_estructuras"] = df.copy()


# =========================================================
# 🔷 NORMALIZACIÓN (ANTI DUPLICADOS)
# =========================================================
def normalizar_df(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()

    # limpiar texto
    df["Estructura"] = df["Estructura"].astype(str).str.upper().str.strip()
    df["Punto"] = df["Punto"].astype(str).str.upper().str.strip()

    # normalizar puntos → P-01
    def fix_punto(p):
        m = re.search(r"P-(\d+)", p)
        if m:
            return f"P-{int(m.group(1)):02d}"
        return p

    df["Punto"] = df["Punto"].apply(fix_punto)

    # eliminar duplicados reales
    df = df.drop_duplicates(subset=["Punto", "Estructura"])

    return df


# =========================================================
# 🔷 AUDITORÍA REAL
# =========================================================
def auditar_estructuras():

    st.markdown("## 🔍 AUDITORÍA REAL")

    df = st.session_state.get("df_estructuras")

    if df is None:
        st.error("❌ df_estructuras NO existe")
        return

    if df.empty:
        st.error("❌ df_estructuras está vacío")
        return

    # normalizar antes de analizar
    df = normalizar_df(df)

    # guardar versión limpia
    st.session_state["df_estructuras_clean"] = df

    # -----------------------------------------------------
    # INFO GENERAL
    # -----------------------------------------------------
    st.success("✔ df cargado correctamente")
    st.write("Shape:", df.shape)
    st.write("Columnas:", list(df.columns))

    st.markdown("### 📊 Preview")
    st.dataframe(df.head(30), use_container_width=True)

    # -----------------------------------------------------
    # CONTEO POR ESTRUCTURA
    # -----------------------------------------------------
    col = "codigodeestructura" if "codigodeestructura" in df.columns else "Estructura"

    st.markdown("### 🔢 Conteo por estructura")
    conteo = df.groupby(col)["Cantidad"].sum().sort_values(ascending=False)
    st.dataframe(conteo)

    # -----------------------------------------------------
    # DETECTAR PROBLEMA PC-30
    # -----------------------------------------------------
    st.markdown("### ⚠️ Validación PC-30")

    df_pc30 = df[df[col].str.contains("PC-30", na=False)]

    puntos_pc30 = df_pc30["Punto"].unique()

    st.write("Total PC-30 detectados:", len(df_pc30))
    st.write("Puntos únicos con PC-30:", len(puntos_pc30))
    st.write("Lista de puntos:", sorted(puntos_pc30))

    # -----------------------------------------------------
    # DUPLICADOS POR PUNTO
    # -----------------------------------------------------
    st.markdown("### 🧨 Duplicados por punto")

    dup = df[df.duplicated(subset=["Punto", col], keep=False)]

    if dup.empty:
        st.success("✔ No hay duplicados")
    else:
        st.error("❌ DUPLICADOS DETECTADOS")
        st.dataframe(dup)

    # -----------------------------------------------------
    # CONTEO POR PUNTO
    # -----------------------------------------------------
    st.markdown("### 📍 Conteo por punto")

    puntos = df["Punto"].value_counts().sort_index()
    st.dataframe(puntos)


# =========================================================
# 🔷 USO EN TU APP
# =========================================================
def ejecutar_debug_completo():

    st.title("🧠 DEBUG REAL DEL SISTEMA")

    auditar_estructuras()
