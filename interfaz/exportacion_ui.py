# interfaz/exportacion_ui.py
# SOLO UI — SIN LÓGICA DE NEGOCIO

import streamlit as st
import pandas as pd

from entradas.estructuras import procesar_estructuras
from materiales.orquestador_materiales import ejecutar_materiales
from reportes.orquestador_reportes import generar_reportes, resumen_estructuras

# =========================================================
# VISTA PREVIA (UI)
# =========================================================
def _vista_previa_conteo(df: pd.DataFrame):

    if df is None or df.empty:
        st.info("No hay datos para mostrar.")
        return

    # 🔥 MOVIDO A DOMINIO (YA NO HAY GROUPBY EN UI)
    conteo = resumen_estructuras(df)

    st.caption("Conteo rápido de estructuras por punto:")
    st.dataframe(conteo, use_container_width=True, hide_index=True)


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

    if not ejecutar:
        if st.session_state.get("resultado_calculo"):
            st.success("✅ Ya hay resultados calculados.")
        else:
            st.caption("Presiona el botón para calcular.")
        return

    try:
        # =====================================================
        # 1. PROCESAR ESTRUCTURAS (DOMINIO)
        # =====================================================
        df_estructuras = procesar_estructuras(df)

        if df_estructuras.empty:
            st.error("❌ No hay estructuras válidas después del procesamiento.")
            return

        st.session_state["df_estructuras"] = df_estructuras

        # =====================================================
        # 2. MATERIALES EXTRA
        # =====================================================
        materiales_extra = pd.DataFrame(
            st.session_state.get("materiales_extra", [])
        )

        # =====================================================
        # 3. DATOS PROYECTO
        # =====================================================
        datos_proyecto = {
            "materiales_extra": materiales_extra
        }

        # =====================================================
        # 4. RUTA MATERIALES
        # =====================================================
        ruta_materiales = st.session_state.get("ruta_datos_materiales")

        if not ruta_materiales:
            st.error("❌ No hay ruta de materiales definida.")
            return

        # =====================================================
        # 5. CABLES (OPCIONAL)
        # =====================================================
        df_cables = st.session_state.get("cables_proyecto_df")

        # =====================================================
        # 6. CALCULAR (SERVICIO)
        # =====================================================
        resultado = calcular_materiales(
            estructuras_df=df_estructuras,
            archivo_materiales=ruta_materiales,
            datos_proyecto=datos_proyecto,
            df_cables=df_cables,
        )

        st.session_state["resultado_calculo"] = resultado
        st.session_state["calculo_finalizado"] = True

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

    df_prev = st.session_state.get("df_estructuras")

    if isinstance(df_prev, pd.DataFrame) and not df_prev.empty:
        _vista_previa_conteo(df_prev)

    # =====================================================
    # BOTÓN GENERAR
    # =====================================================
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

    # =====================================================
    # DESCARGAS
    # =====================================================
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
