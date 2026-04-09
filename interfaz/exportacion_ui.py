# -*- coding: utf-8 -*-
# interfaz/exportacion_ui.py

from __future__ import annotations

import pandas as pd
import streamlit as st

# =========================
# APLICACIÓN
# =========================
from aplicacion.orquestador_sistema import ejecutar_sistema

# =========================
# CONTRATOS
# =========================
from interfaz.contratos import SalidaInterfaz


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


def _debug_final(data):
    st.markdown("### 🧠 Debug previo a cálculo")

    st.write("Tipo de data:", type(data))

    if isinstance(data, pd.DataFrame):
        st.write("Columnas:", list(data.columns))


# =========================================================
# FINALIZAR CÁLCULO
# =========================================================
def seccion_finalizar_calculo():

    st.subheader("⚙️ Finalizar cálculo")

    data = st.session_state.get("data_entrada")
    datos = st.session_state.get("datos_proyecto", {})

    if data is None:
        st.warning("Debe ingresar estructuras antes de calcular")
        return

    _debug_final(data)

    if isinstance(data, pd.DataFrame):
        _vista_previa_conteo(data)

    # =====================================================
    # EJECUCIÓN SISTEMA
    # =====================================================
    if st.button("🚀 Ejecutar cálculo"):

        df_estructuras = st.session_state.get("df_estructuras")

        if df_estructuras is None:
            st.error("❌ No hay estructuras procesadas")
            return

        try:

            # =================================================
            # CONTRATO UI → SISTEMA
            # =================================================
            salida_interfaz = SalidaInterfaz(
                ok=True,
                tipo_entrada="tabla",
                data_entrada=df_estructuras,
                datos_proyecto=datos,
            )

            # =================================================
            # EJECUCIÓN CENTRAL
            # =================================================
            with st.spinner("Ejecutando sistema completo..."):
                resultado = ejecutar_sistema(salida_interfaz)

            # =================================================
            # VALIDACIÓN RESULTADO
            # =================================================
            if not resultado or not resultado.ok:

                st.error("❌ Error en cálculo")

                for err in getattr(resultado, "errores", []):
                    st.error(f"• {err}")

                for w in getattr(resultado, "warnings", []):
                    st.warning(f"⚠️ {w}")

                if hasattr(resultado, "debug"):
                    with st.expander("🧠 Debug técnico"):
                        st.json(resultado.debug)

                return

            # =================================================
            # SUCCESS
            # =================================================
            st.session_state["resultado_calculo"] = resultado
            st.session_state["calculo_finalizado"] = True

            st.success("✅ Sistema ejecutado correctamente")

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
                reportes = resultado.reportes

                if reportes is None:
                    st.error("❌ El sistema no devolvió reportes")
                    return

                archivos = reportes.archivos
                errores = reportes.errores

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
