# -*- coding: utf-8 -*-
# interfaz/exportacion_ui.py

from __future__ import annotations

import pandas as pd
import streamlit as st

# =========================
# APLICACIÓN (ÚNICO ORQUESTADOR)
# =========================
from aplicacion.orquestador_proyecto import ejecutar_proyecto

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


def _debug_final(df_estructuras):
    st.markdown("### 🧠 Debug previo a cálculo")

    st.write("Tipo:", type(df_estructuras))

    if isinstance(df_estructuras, pd.DataFrame):
        st.write("Columnas:", list(df_estructuras.columns))
        st.write("Filas:", len(df_estructuras))


# =========================================================
# FINALIZAR CÁLCULO
# =========================================================
def seccion_finalizar_calculo():

    st.subheader("⚙️ Finalizar cálculo")

    df_estructuras = st.session_state.get("df_estructuras")

    # =====================================================
    # VALIDACIÓN FUERTE UI
    # =====================================================
    if df_estructuras is None or df_estructuras.empty:
        st.warning("Debe ingresar estructuras antes de calcular")
        return

    _debug_final(df_estructuras)
    _vista_previa_conteo(df_estructuras)

    # =====================================================
    # EJECUCIÓN
    # =====================================================
    if st.button("🚀 Ejecutar cálculo"):

        try:

            # =================================================
            # CONTRATO UI → DOMINIO
            # =================================================
            salida_interfaz = SalidaInterfaz(
                ok=True,
                tipo_entrada="tabla",
                data_entrada=df_estructuras,
                datos_proyecto=st.session_state.get("datos_proyecto", {}),
                df_cables=st.session_state.get("df_cables"),
                df_materiales_extra=st.session_state.get("df_materiales_extra"),
            )

            # =================================================
            # ORQUESTADOR
            # =================================================
            with st.spinner("Ejecutando proyecto..."):
                resultado = ejecutar_proyecto(salida_interfaz)

            # =================================================
            # VALIDACIÓN RESULTADO
            # =================================================
            if resultado is None:
                st.error("❌ El sistema no devolvió resultado")
                return

            if not getattr(resultado, "ok", False):

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

            st.success("✅ Proyecto ejecutado correctamente")

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

    archivos = getattr(reportes, "archivos", None)
    errores = getattr(reportes, "errores", [])

    if not archivos:
        st.warning("No se generaron archivos")
        return

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

        st.download_button(
            label=f"Descargar {nombre}",
            data=archivo,
            file_name=nombre,
            mime="application/octet-stream"
        )
