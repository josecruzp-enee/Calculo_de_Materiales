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

    if df_estructuras is None or df_estructuras.empty:
        st.info("No hay estructuras cargadas")
        return

    st.caption("Vista previa de estructuras")

    try:
        resumen = df_estructuras.value_counts().reset_index(name="Cantidad")
        st.dataframe(resumen, use_container_width=True)
    except Exception:
        st.dataframe(df_estructuras, use_container_width=True)


def _debug_final(tension, data):
    st.markdown("### 🧠 Debug previo a cálculo")

    st.write("Tensión:", tension)
    st.write("Tipo de data:", type(data))

    if isinstance(data, pd.DataFrame):
        st.write("Columnas:", list(data.columns))


# =========================================================
# FINALIZAR CÁLCULO
# =========================================================
def seccion_finalizar_calculo():

    st.subheader("⚙️ Finalizar cálculo")

    tipo = st.session_state.get("modo_carga_seleccionado")
    data = st.session_state.get("data_entrada")
    datos = st.session_state.get("datos_proyecto", {})
    tension_raw = datos.get("nivel_de_tension")

    if not tension_raw:
        st.error("❌ No se encontró tensión en datos del proyecto")
        return

    try:
        tension = 34.5 if "34.5" in str(tension_raw) else 13.8
    except Exception:
        st.error(f"❌ Error interpretando tensión: {tension_raw}")
        return

    if data is None:
        st.warning("Debe ingresar estructuras antes de calcular")
        return

    _debug_final(tension, data)

    if isinstance(data, pd.DataFrame):
        _vista_previa_conteo(data)

    # =====================================================
    # EJECUCIÓN (YA NO LLAMA ENTRADAS)
    # =====================================================
    if st.button("🚀 Ejecutar cálculo"):

        # 🔥 Tomar datos del pipeline correcto
        df_estructuras = st.session_state.get("df_estructuras")

        if df_estructuras is None:
            st.error("❌ No hay estructuras procesadas. Ejecuta primero el flujo de entradas.")
            return

        base_datos = st.session_state.get("base_datos")

        # ⚠️ No rompe si aún no migras base_datos
        if base_datos is None:
            st.warning("⚠️ base_datos no encontrado (modo compatibilidad activado)")

        try:
            entrada_proyecto = EntradaProyecto(
                df_estructuras=df_estructuras,
                base_datos=base_datos,  # 🔥 NUEVO
                tension=float(tension),
            )

            with st.spinner("Calculando materiales..."):
                resultado = ejecutar_proyecto(entrada_proyecto)

            # ===============================
            # MANEJO DE ERRORES
            # ===============================
            if not resultado or not resultado.ok:
                st.error("❌ Error en cálculo")

                if hasattr(resultado, "errores"):
                    for err in resultado.errores:
                        st.error(f"• {err}")

                if hasattr(resultado, "warnings"):
                    for w in resultado.warnings:
                        st.warning(f"⚠️ {w}")

                if hasattr(resultado, "debug"):
                    with st.expander("🧠 Debug técnico"):
                        st.json(resultado.debug)

                return

            # ===============================
            # WARNINGS
            # ===============================
            if resultado.warnings:
                for w in resultado.warnings:
                    st.warning(w)

            st.session_state["resultado_calculo"] = resultado
            st.session_state["calculo_finalizado"] = True

            st.success("✅ Cálculo completado correctamente")

        except Exception as e:
            import traceback

            st.error(f"❌ Error general: {str(e)}")

            with st.expander("🧠 Traceback completo"):
                st.code(traceback.format_exc())


# =========================================================
# EXPORTACIÓN
# =========================================================
def seccion_exportacion():

    st.subheader("📤 Exportación de resultados")

    resultado = st.session_state.get("resultado_calculo")
    calculo_ok = st.session_state.get("calculo_finalizado")

    if not calculo_ok or resultado is None:
        st.info("Debe ejecutar el cálculo antes de exportar")
        return

    # =====================================================
    # GENERAR REPORTES
    # =====================================================
    if st.button("📄 Generar reportes"):

        with st.spinner("Generando archivos..."):

            try:
                mat = resultado.materiales

                data_export = {
                    "df_estructuras": st.session_state.get("df_estructuras"),
                    "df_materiales": mat.df_materiales,
                    "df_resumen": mat.df_materiales,
                    "df_por_punto": getattr(mat, "df_materiales_por_punto", None),
                }

                st.write("DEBUG EXPORT:", {
                    k: type(v).__name__ for k, v in data_export.items()
                })

                out = generar_reportes(data_export)

                archivos = out.get("archivos", {})
                errores = out.get("errores", [])

            except Exception as e:
                st.error(f"Error generando reportes: {e}")
                return

        if not archivos:
            st.warning("No se generaron archivos")
            return

        st.session_state["pdfs_generados"] = archivos

        st.success("Reportes generados correctamente")

        if errores:
            st.error("Algunos reportes fallaron:")
            for e in errores:
                st.error(e)

    # =====================================================
    # DESCARGAS
    # =====================================================
    pdfs = st.session_state.get("pdfs_generados")

    if pdfs:

        st.markdown("### 📥 Descargar archivos")

        for nombre, archivo in pdfs.items():

            if not isinstance(archivo, (bytes, bytearray)):
                st.error(f"{nombre} tipo inválido: {type(archivo)}")
                continue

            st.download_button(
                label=f"Descargar {nombre}",
                data=archivo,
                file_name=nombre,
                mime="application/octet-stream"
            )
