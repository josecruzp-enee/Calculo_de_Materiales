# -*- coding: utf-8 -*-
# interfaz/exportacion_ui.py
# SOLO UI — SIN LÓGICA DE NEGOCIO

from __future__ import annotations

import streamlit as st
import pandas as pd

# =========================
# APLICACIÓN (🔥 NUEVO)
# =========================
from aplicacion.orquestador_proyecto import ejecutar_proyecto

# =========================
# REPORTES
# =========================
from exportadores.orquestador_reportes import generar_reportes, resumen_estructuras


# =========================================================
# VISTA PREVIA (UI)
# =========================================================
def _vista_previa_conteo(df: pd.DataFrame):

    if df is None or df.empty:
        st.info("No hay datos para mostrar.")
        return

    conteo = resumen_estructuras(df)

    st.caption("Conteo rápido de estructuras por punto:")
    st.dataframe(conteo, width="stretch", hide_index=True)


# =========================================================
# FINALIZAR (CALCULAR)
# =========================================================
def seccion_finalizar_calculo(df: pd.DataFrame):

    st.subheader("5. 🏁 Finalizar Cálculo del Proyecto")

    if df is None or df.empty:
        st.info("⚠️ No hay estructuras cargadas.")
        return

    with st.form("form_finalizar_calculo"):
        ejecutar = st.form_submit_button("✅ Finalizar Cálculo")

    # =========================
    # SI NO PRESIONA
    # =========================
    if not ejecutar:
        if st.session_state.get("resultado_calculo"):
            st.success("✅ Ya hay resultados calculados.")
        else:
            st.caption("Presiona el botón para calcular.")
        return

    # =========================
    # EJECUCIÓN
    # =========================
    try:

        resultado, errores, warnings = ejecutar_proyecto(
            df,
            st.session_state
        )

        if resultado is None:
            for err in errores:
                st.error(f"❌ {err}")
            return

        if not resultado.ok:
            st.error("❌ Error en cálculo:")
            for err in resultado.errores:
                st.write(f"- {err}")
            return

        # Guardar estado
        st.session_state["resultado_calculo"] = resultado
        st.session_state["calculo_finalizado"] = True

        # Mostrar warnings si existen
        if getattr(resultado, "warnings", None):
            for w in resultado.warnings:
                st.warning(f"⚠️ {w}")

        st.success("🎉 Cálculo finalizado correctamente.")

    except Exception as e:
        st.session_state["calculo_finalizado"] = False
        st.error(f"❌ Error en cálculo: {e}")
        st.stop()


# =========================================================
# EXPORTACIÓN (PDF)
# =========================================================
def seccion_exportacion():

    st.subheader("6. 📂 Exportación de Reportes")

    resultado = st.session_state.get("resultado_calculo")

    if not resultado:
        st.warning("⚠️ Primero debes finalizar el cálculo.")
        return

    # Vista previa
    df_prev = st.session_state.get("df_estructuras")

    if isinstance(df_prev, pd.DataFrame) and not df_prev.empty:
        _vista_previa_conteo(df_prev)

    # =========================
    # BOTÓN GENERAR
    # =========================
    with st.form("form_generar_reportes"):
        generar = st.form_submit_button("📥 Generar Reportes PDF")

    if generar:

        try:
            with st.spinner("⏳ Generando reportes..."):
                pdfs = generar_reportes(resultado)

            st.session_state["pdfs_generados"] = pdfs

            st.success("✅ Reportes generados correctamente")

        except Exception as e:
            st.error(f"❌ Error generando reportes: {e}")
            return

    # =========================
    # DESCARGAS
    # =========================
    pdfs = st.session_state.get("pdfs_generados")

    if not pdfs:
        st.info("Presiona generar reportes.")
        return

    st.markdown("### 📥 Descargas")

    for nombre, archivo in pdfs.items():

        if archivo:
            st.download_button(
                f"📄 Descargar {nombre}",
                archivo,
                f"{nombre}.pdf",
                "application/pdf"
            )
