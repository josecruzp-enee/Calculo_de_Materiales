# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import datetime


# =========================================================
# 🔷 CONFIG
# =========================================================
DEBUG_ACTIVO = True


# =========================================================
# 🔷 INIT
# =========================================================
def _init_debug():
    if "debug_pipeline" not in st.session_state:
        st.session_state["debug_pipeline"] = []


# =========================================================
# 🔷 DEBUG PRINCIPAL (ULTRA FLEXIBLE)
# =========================================================
def debug_guardar(*args):
    """
    SOPORTA:
    ✔ debug_guardar(clave, valor)
    ✔ debug_guardar(etapa, clave, valor)
    ✔ debug_guardar(dominio, etapa, clave, valor)
    """

    if not DEBUG_ACTIVO:
        return

    _init_debug()

    timestamp = datetime.now().strftime("%H:%M:%S")

    # =====================================================
    # PARSEO INTELIGENTE
    # =====================================================
    dominio = "GENERAL"
    etapa = "INFO"
    clave = "VALOR"
    valor = None

    if len(args) == 2:
        clave, valor = args

    elif len(args) == 3:
        etapa, clave, valor = args

    elif len(args) == 4:
        dominio, etapa, clave, valor = args

    else:
        clave = "DEBUG_ERROR"
        valor = f"Argumentos inválidos: {args}"

    # =====================================================
    # GUARDAR
    # =====================================================
    registro = {
        "time": timestamp,
        "dominio": dominio,
        "etapa": etapa,
        "clave": clave,
        "valor": valor,
    }

    st.session_state["debug_pipeline"].append(registro)

    # =====================================================
    # PRINT CONSOLA (🔥 CLAVE)
    # =====================================================
    try:
        print(f"[{timestamp}] [{dominio}] [{etapa}] {clave} -> {str(valor)[:200]}")
    except:
        print(f"[{timestamp}] [{dominio}] [{etapa}] {clave} -> (valor no imprimible)")


# =========================================================
# 🔷 LIMPIAR
# =========================================================
def debug_limpiar():
    st.session_state["debug_pipeline"] = []


# =========================================================
# 🔷 VISOR PRO
# =========================================================
def seccion_debug():

    st.subheader("🧠 Debug del sistema")

    data = st.session_state.get("debug_pipeline", [])

    if not data:
        st.info("No hay debug aún")
        return

    df = pd.DataFrame(data)

    # =====================================================
    # FILTROS
    # =====================================================
    col1, col2 = st.columns(2)

    with col1:
        dominios = ["Todos"] + sorted(df["dominio"].unique())
        dom_sel = st.selectbox("Dominio", dominios)

    with col2:
        etapas = ["Todos"] + sorted(df["etapa"].unique())
        etapa_sel = st.selectbox("Etapa", etapas)

    df_filtrado = df.copy()

    if dom_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado["dominio"] == dom_sel]

    if etapa_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado["etapa"] == etapa_sel]

    # =====================================================
    # TABLA PRINCIPAL
    # =====================================================
    st.dataframe(df_filtrado, use_container_width=True)

    # =====================================================
    # DETALLE EXPANDIBLE
    # =====================================================
    st.markdown("### 🔍 Detalle")

    for i, row in df_filtrado.iterrows():

        with st.expander(f"{row['time']} | {row['clave']}"):

            val = row["valor"]

            if isinstance(val, pd.DataFrame):
                st.dataframe(val)

            elif isinstance(val, (dict, list)):
                st.json(val)

            else:
                st.write(val)

    # =====================================================
    # BOTONES
    # =====================================================
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🧹 Limpiar debug"):
            debug_limpiar()
            st.success("Debug limpiado")

    with col2:
        if st.button("📥 Exportar CSV"):
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("Descargar", csv, "debug.csv", "text/csv")
