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
# DEBUG CONTROLADO
# =========================================================
def _debug_final(tension, data):
    st.markdown("### 🧠 Debug previo a cálculo")

    st.write("Tensión en session_state:", tension)
    st.write("Tipo de data:", type(data))

    if isinstance(data, pd.DataFrame):
        st.write("Filas:", len(data))
        st.write("Columnas:", list(data.columns))


# =========================================================
# SECCIÓN FINALIZAR
# =========================================================
def seccion_finalizar_calculo():

    from interfaz.contratos import SalidaInterfaz
    from entradas.orquestador_entradas import ejecutar_entradas

    st.subheader("⚙️ Finalizar cálculo")

    tipo = st.session_state.get("modo_carga_seleccionado")
    data = st.session_state.get("data_entrada")
    tension = st.session_state.get("tension")  # 🔥 CLAVE

    # =====================================================
    # VALIDACIONES
    # =====================================================
    if data is None:
        st.warning("Debe ingresar estructuras antes de calcular")
        return

    if tension is None:
        st.error("❌ Tensión no definida. Seleccione 13.8 kV o 34.5 kV en 'Modo de Carga'")
        return

    # =====================================================
    # DEBUG (clave para no volvernos locos)
    # =====================================================
    _debug_final(tension, data)

    # =====================================================
    # Vista previa (solo manual)
    # =====================================================
    if isinstance(data, pd.DataFrame):
        _vista_previa_conteo(data)

    # =====================================================
    # EJECUCIÓN
    # =====================================================
    if st.button("🚀 Ejecutar cálculo"):

        try:
            # =====================================================
            # 1. CONTRATO INTERFAZ
            # =====================================================
            salida_ui = SalidaInterfaz(
                ok=True,
                tipo_entrada=tipo,
                data_entrada=data,
                datos_proyecto=st.session_state.get("datos_proyecto", {}),
                df_cables=st.session_state.get("cables_proyecto_df"),
                df_materiales_extra=pd.DataFrame(
                    st.session_state.get("materiales_extra", [])
                ),
            )

            # =====================================================
            # 2. ENTRADAS (CON TENSIÓN REAL)
            # =====================================================
            salida_entradas = ejecutar_entradas(
                salida_ui,
                tension=float(tension)  # 🔥 YA NO HARDCODE
            )

            if not salida_entradas.ok:
                st.error("❌ Error en entradas:")
                for e in salida_entradas.errores:
                    st.error(f"- {e}")
                return

            st.session_state["df_estructuras"] = salida_entradas.df_estructuras

            # =====================================================
            # 3. ADAPTADOR → PROYECTO
            # =====================================================
            entrada_proyecto = EntradaProyecto(
                df_estructuras=salida_entradas.df_estructuras,
                df_cables=salida_entradas.df_cables,
                df_materiales_extra=salida_entradas.df_materiales_extra,
                ruta_materiales=st.session_state.get("ruta_datos_materiales"),
                tension=float(tension),  # 🔥 CRÍTICO
            )

            # =====================================================
            # 4. EJECUCIÓN PROYECTO
            # =====================================================
            with st.spinner("Calculando materiales..."):
                resultado = ejecutar_proyecto(entrada_proyecto)

            if resultado is None:
                st.error("❌ Resultado vacío")
                return

            if not resultado.ok:
                st.error("❌ Error en el cálculo:")
                for e in resultado.errores:
                    st.error(f"- {e}")
                return

            if resultado.warnings:
                for w in resultado.warnings:
                    st.warning(w)

            # =====================================================
            # 5. GUARDAR RESULTADO
            # =====================================================
            st.session_state["resultado_calculo"] = resultado
            st.session_state["calculo_finalizado"] = True

            st.success("✅ Cálculo completado correctamente")

        except Exception as e:
            st.error(f"❌ Error general: {str(e)}")


# =========================================================
# SECCIÓN EXPORTACIÓN
# =========================================================
def seccion_exportacion():

    st.subheader("📤 Exportación de resultados")

    resultado = st.session_state.get("resultado_calculo")
    calculo_ok = st.session_state.get("calculo_finalizado")

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    if not calculo_ok or resultado is None:
        st.info("Debe ejecutar el cálculo antes de exportar")
        return

    # =====================================================
    # GENERAR REPORTES
    # =====================================================
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

    # =====================================================
    # DESCARGAS
    # =====================================================
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
