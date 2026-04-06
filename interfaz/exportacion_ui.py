# -*- coding: utf-8 -*-
# interfaz/exportacion_ui.py

from __future__ import annotations

import pandas as pd
import streamlit as st

# =========================
# APLICACIÓN
# =========================
from aplicacion.modelos_proyecto import EntradaProyecto
from aplicacion.orquestador_proyecto import ejecutar_proyecto

# =========================
# EXPORTADORES
# =========================
from exportadores.orquestador_reportes import generar_reportes


# =========================================================
# HELPERS
# =========================================================
def _vista_previa_conteo(df_estructuras: pd.DataFrame | None):
    """
    Vista rápida antes de ejecutar cálculo
    """

    if df_estructuras is None or df_estructuras.empty:
        st.info("No hay estructuras cargadas")
        return

    st.caption("Vista previa de estructuras")

    try:
        resumen = df_estructuras.value_counts().reset_index(name="Cantidad")
        st.dataframe(resumen, use_container_width=True)
    except Exception:
        st.dataframe(df_estructuras, use_container_width=True)


# =========================================================
# SECCIÓN FINALIZAR
# =========================================================
def seccion_finalizar_calculo():

    st.subheader("⚙️ Finalizar cálculo")

    df_estructuras = st.session_state.get("df_estructuras")

    # =========================
    # VALIDACIÓN
    # =========================
    if df_estructuras is None or df_estructuras.empty:
        st.warning("Debe ingresar estructuras antes de calcular")
        return

    _vista_previa_conteo(df_estructuras)

    # =========================
    # BOTÓN EJECUCIÓN
    # =========================
    if st.button("🚀 Ejecutar cálculo"):

        # =========================
        # ARMAR DTO
        # =========================
        entrada = EntradaProyecto(
            df_estructuras=df_estructuras,
            df_cables=st.session_state.get("cables_proyecto_df"),
            df_materiales_extra=pd.DataFrame(
                st.session_state.get("materiales_extra", [])
            ),
            ruta_materiales=st.session_state.get("ruta_datos_materiales"),
        )

        # =========================
        # EJECUTAR ORQUESTADOR
        # =========================
        with st.spinner("Calculando materiales..."):
            resultado = ejecutar_proyecto(entrada)

        # =========================
        # VALIDAR RESULTADO
        # =========================
        if resultado is None:
            st.error("❌ Resultado vacío")
            return

        if not resultado.ok:
            st.error("❌ Error en el cálculo:")
            for e in resultado.errores:
                st.error(f"- {e}")
            return

        # =========================
        # WARNINGS
        # =========================
        if resultado.warnings:
            for w in resultado.warnings:
                st.warning(w)

        # =========================
        # GUARDAR RESULTADO
        # =========================
        st.session_state["resultado_calculo"] = resultado
        st.session_state["calculo_finalizado"] = True

        st.success("✅ Cálculo completado correctamente")


# =========================================================
# SECCIÓN EXPORTACIÓN
# =========================================================
def seccion_exportacion():

    st.subheader("📤 Exportación de resultados")

    resultado = st.session_state.get("resultado_calculo")
    calculo_ok = st.session_state.get("calculo_finalizado")

    # =========================
    # VALIDACIÓN
    # =========================
    if not calculo_ok or resultado is None:
        st.info("Debe ejecutar el cálculo antes de exportar")
        return

    # =========================
    # GENERAR REPORTES
    # =========================
    if st.button("📄 Generar reportes"):

        with st.spinner("Generando archivos..."):

            try:
                pdfs = generar_reportes(resultado)

            except Exception as e:
                st.error(f"Error generando reportes: {e}")
                return

        if not pdfs:
            st.warning("No se generaron archivos")
            return

        st.session_state["pdfs_generados"] = pdfs

        st.success("Reportes generados correctamente")

    # =========================
    # DESCARGAS
    # =========================
    pdfs = st.session_state.get("pdfs_generados")

    if pdfs:

        st.markdown("### 📥 Descargar archivos")

        for nombre, archivo in pdfs.items():
            st.download_button(
                label=f"Descargar {nombre}",
                data=archivo,
                file_name=nombre,
                mime="application/pdf"
            )
