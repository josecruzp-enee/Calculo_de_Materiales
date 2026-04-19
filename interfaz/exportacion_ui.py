# -*- coding: utf-8 -*-
# interfaz/exportacion_ui.py

from __future__ import annotations

import pandas as pd
import streamlit as st


# =========================================================
# HELPERS
# =========================================================
def _vista_previa_conteo(df_estructuras: pd.DataFrame | None):

    if df_estructuras is None or df_estructuras.empty:
        st.info("No hay estructuras cargadas")
        return

    st.caption("Vista previa de estructuras")

    try:
        resumen = df_estructuras.value_counts().reset_index(name="Cantidad")
        st.dataframe(resumen, use_container_width=True)
    except Exception:
        st.dataframe(df_estructuras, use_container_width=True)


def _debug_final(df_estructuras):
    st.markdown("### 🧠 Debug previo a cálculo")

    st.write("Tipo:", type(df_estructuras))

    if isinstance(df_estructuras, pd.DataFrame):
        st.write("Columnas:", list(df_estructuras.columns))
        st.write("Filas:", len(df_estructuras))


# =========================================================
# 🔥 NUEVO HELPER NOMBRE ARCHIVO
# =========================================================
def _nombre_archivo(nombre_base: str, datos_proyecto: dict) -> str:
    nombre_proy = datos_proyecto.get("nombre_proyecto", "Proyecto")

    mapa = {
        "materiales.pdf": "Materiales",
        "estructuras_global.pdf": "Estructuras Global",
        "estructuras_por_punto.pdf": "Estructuras por Punto",
        "materiales_por_punto.pdf": "Materiales por Punto",
        "reporte_completo.pdf": "Reporte Completo",
    }

    tipo = mapa.get(nombre_base, nombre_base.replace(".pdf", ""))

    return f"{tipo} - {nombre_proy}.pdf"


# =========================================================
# EXPORTACIÓN
# =========================================================
def seccion_exportacion():

    st.subheader("📤 Exportación de resultados")

    resultado = st.session_state.get("resultado_calculo")

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    if resultado is None:
        st.info("Debe ejecutar el cálculo antes de exportar")
        return

    if not getattr(resultado, "ok", False):
        st.error("❌ El cálculo no es válido")
        return

    reportes = getattr(resultado, "reportes", None)

    if reportes is None:
        st.error("❌ El resultado no contiene reportes")
        return

    archivos = reportes.get("archivos", {})
    errores = reportes.get("errores", [])

    if not archivos:
        st.warning("No se generaron archivos")
        return

    # 🔥 obtener datos del proyecto (sin romper nada)
    datos_proyecto = getattr(resultado, "datos_proyecto", {}) or {}

    # =====================================================
    # UI
    # =====================================================
    st.success("Reportes disponibles")

    if errores:
        st.warning("Algunos reportes fallaron:")
        for e in errores:
            st.warning(e)

    st.markdown("### 📥 Descargar archivos")

    for nombre, archivo in archivos.items():

        if not isinstance(archivo, (bytes, bytearray)):
            st.error(f"{nombre} tipo inválido: {type(archivo)}")
            continue

        # 🔥 nombre profesional
        nombre_final = _nombre_archivo(nombre, datos_proyecto)

        st.download_button(
            label=f"Descargar {nombre_final.replace('.pdf','')}",
            data=archivo,
            file_name=nombre_final,
            mime="application/pdf"
        )
