# -*- coding: utf-8 -*-
# interfaz/exportacion.py

import re
import pandas as pd
import streamlit as st
from modulo.procesar_materiales import procesar_materiales

# Regex precompiladas para rendimiento
_RE_SPLIT = re.compile(r"[+,;]")
_RE_SANIT = re.compile(r"[^A-Z0-9\-\.]")

COLUMNAS_ESTRUCTURAS = ["Poste", "Primario", "Secundario", "Retenidas", "Conexiones a tierra", "Transformadores"]

def _limpiar_listado(valor: str) -> list[str]:
    """Normaliza una celda de estructuras en lista limpia sin duplicados preservando orden."""
    if not valor or str(valor).strip().lower() == 'seleccionar estructura':
        return []
    out = []
    for p in _RE_SPLIT.split(str(valor)):
        t = _RE_SANIT.sub("", p.strip().upper())
        if t and t not in {"SELECCIONAR", "ESTRUCTURA", "N/A", "NONE"}:
            out.append(t)
    vistos, res = set(), []
    for x in out:
        if x not in vistos:
            res.append(x); vistos.add(x)
    return res

def _expandir_estructuras(df: pd.DataFrame) -> pd.DataFrame:
    """Crea df_expandido con una fila por (Punto, codigodeestructura) sin duplicados."""
    df2 = df.copy()
    df2["Estructura"] = df2.apply(
        lambda fila: sum((_limpiar_listado(fila.get(c, "")) for c in COLUMNAS_ESTRUCTURAS), []),
        axis=1
    )
    df2 = df2.explode("Estructura", ignore_index=True)
    df2 = df2[df2["Estructura"].notna() & (df2["Estructura"].str.strip() != "")]
    df2["Estructura"] = df2["Estructura"].str.strip().str.upper()
    df2.drop_duplicates(subset=["Punto", "Estructura"], inplace=True)
    df2.rename(columns={"Estructura": "codigodeestructura"}, inplace=True)
    return df2

def _preview_conteo(df_expandido: pd.DataFrame) -> None:
    conteo = (
        df_expandido.groupby(["Punto", "codigodeestructura"])
        .size()
        .reset_index(name="Cantidad")
    )
    st.caption("Conteo rápido de estructuras por punto (sin duplicados):")
    st.dataframe(conteo, use_container_width=True, hide_index=True)

def seccion_finalizar_calculo(df: pd.DataFrame) -> None:
    if not df.empty:
        st.subheader("5. 🏁 Finalizar Cálculo del Proyecto")
        if st.button("✅ Finalizar Cálculo", key="btn_finalizar_calculo"):
            st.session_state["calculo_finalizado"] = True
            st.success("🎉 Cálculo finalizado con éxito. Ahora puedes exportar los reportes.")

def seccion_exportacion(
    df: pd.DataFrame,
    modo_carga: str,
    ruta_estructuras: str | None,
    ruta_datos_materiales: str
) -> None:
    """Exportación de reportes PDF/Excel. Sincroniza cables, expande estructuras y genera PDFs."""
    if df.empty or not st.session_state.get("calculo_finalizado", False):
        return

    st.subheader("6. 📂 Exportación de Reportes")

    # 1) Sincronizar datos de cables a datos_proyecto (con defaults suaves)
    if "cables_proyecto" in st.session_state:
        st.session_state["datos_proyecto"]["cables_proyecto"] = st.session_state["cables_proyecto"]

        datos_cables = st.session_state["cables_proyecto"]
        if isinstance(datos_cables, list) and len(datos_cables) > 0:
            datos_cables = datos_cables[0]
        elif not isinstance(datos_cables, dict):
            datos_cables = {}

        tension = datos_cables.get("tension") or datos_cables.get("nivel_de_tension") or 13.8
        calibre_mt = (
            datos_cables.get("calibre_mt")
            or datos_cables.get("conductor_mt")
            or datos_cables.get("Calibre")
            or "1/0 ASCR"
        )
        st.session_state["datos_proyecto"]["tension"] = tension
        st.session_state["datos_proyecto"]["calibre_mt"] = calibre_mt
        st.info(f"🔧 Nivel de tensión: {tension} kV  |  Calibre MT: {calibre_mt}")

    # 2) Expandir estructuras
    df_expandido = _expandir_estructuras(df)
    _preview_conteo(df_expandido)

    # 3) Materiales adicionales → DataFrame
    if st.session_state.get("materiales_extra"):
        st.session_state["datos_proyecto"]["materiales_extra"] = pd.DataFrame(st.session_state["materiales_extra"])
    else:
        st.session_state["datos_proyecto"]["materiales_extra"] = pd.DataFrame(
            columns=["Materiales", "Unidad", "Cantidad"]
        )

    # 4) Generar reportes
    if st.button("📥 Generar Reportes PDF", key="btn_generar_pdfs"):
        try:
            with st.spinner("⏳ Generando reportes, por favor espere..."):
                resultados_pdf = procesar_materiales(
                    archivo_estructuras=ruta_estructuras,
                    archivo_materiales=ruta_datos_materiales,
                    estructuras_df=df_expandido,
                    datos_proyecto=st.session_state.get("datos_proyecto", {})
                )

            st.session_state["pdfs_generados"] = resultados_pdf
            st.success("✅ Reportes generados correctamente")

            if isinstance(resultados_pdf, dict):
                st.info(f"📄 PDFs generados: {list(resultados_pdf.keys())}")
            else:
                st.warning("⚠️ El módulo procesar_materiales no devolvió un diccionario válido.")
        except Exception as e:
            st.error(f"❌ Error al generar reportes: {e}")

    # 5) Descarga
    if "pdfs_generados" in st.session_state:
        pdfs = st.session_state["pdfs_generados"]
        st.markdown("### 📥 Descarga de Reportes Generados")
        if isinstance(pdfs, dict):
            if pdfs.get("materiales"):
                st.download_button("📄 Descargar PDF de Materiales", pdfs["materiales"],
                                   "Resumen_Materiales.pdf", "application/pdf", key="dl_mat")
            if pdfs.get("estructuras_global"):
                st.download_button("📄 Descargar PDF de Estructuras (Global)", pdfs["estructuras_global"],
                                   "Resumen_Estructuras.pdf", "application/pdf", key="dl_estr_glob")
            if pdfs.get("estructuras_por_punto"):
                st.download_button("📄 Descargar PDF de Estructuras por Punto", pdfs["estructuras_por_punto"],
                                   "Estructuras_Por_Punto.pdf", "application/pdf", key="dl_estr_punto")
            if pdfs.get("materiales_por_punto"):
                st.download_button("📄 Descargar PDF de Materiales por Punto", pdfs["materiales_por_punto"],
                                   "Materiales_Por_Punto.pdf", "application/pdf", key="dl_mat_punto")
            if pdfs.get("completo"):
                st.download_button("📄 Descargar Informe Completo", pdfs["completo"],
                                   "Informe_Completo.pdf", "application/pdf", key="dl_full")
