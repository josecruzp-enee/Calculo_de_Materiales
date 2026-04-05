# interfaz/orquestador_interfaz.py

import streamlit as st
import pandas as pd

from interfaz.base import seleccionar_modo_carga, ruta_datos_materiales_por_defecto
from interfaz.datos_proyecto import seccion_datos_proyecto
from interfaz.cables import seccion_cables_proyecto
from interfaz.estructuras import seccion_entrada_estructuras
from interfaz.materiales_extra import seccion_adicionar_material
from interfaz.exportacion import seccion_finalizar_calculo, seccion_exportacion
from interfaz.mapa_kml import seccion_mapa_kmz


def ejecutar_orquestador_interfaz(
    _nav_estado_actual,
    _barra_nav_botones,
):
    """
    Orquestador de navegación UI.
    """

    seccion = _nav_estado_actual()
    _barra_nav_botones(seccion)

    if seccion == "datos":
        seccion_datos_proyecto()

    elif seccion == "cables":
        seccion_cables_proyecto()

    elif seccion == "modo":
        st.subheader("3) Modo de Carga")
        modo = seleccionar_modo_carga()
        st.session_state["modo_carga_seleccionado"] = modo

    elif seccion == "estructuras":
        modo = st.session_state.get("modo_carga_seleccionado", "Listas desplegables")
        df_estructuras, ruta_estructuras = seccion_entrada_estructuras(modo)

        if df_estructuras is not None and hasattr(df_estructuras, "empty") and not df_estructuras.empty:

            st.session_state["df_estructuras"] = df_estructuras
            st.session_state["ruta_estructuras_compacto"] = ruta_estructuras

            st.session_state.setdefault("datos_proyecto", {})
            st.session_state.setdefault(
                "df_cables",
                pd.DataFrame(columns=["Tipo", "Configuración", "Calibre", "Longitud (m)"]),
            )
            st.session_state.setdefault(
                "df_materiales_extra",
                pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"]),
            )

            st.success("✅ Guardado en memoria.")

        else:
            st.warning("⚠️ No se generaron estructuras.")

    elif seccion == "materiales":
        seccion_adicionar_material()

    elif seccion == "final":
        df_e = st.session_state.get("df_estructuras")

        if df_e is None or df_e.empty:
            st.info("⚠️ Carga estructuras primero.")
        else:
            seccion_finalizar_calculo(df_e)

    elif seccion == "exportar":
        df_e = st.session_state.get("df_estructuras")
        ruta_e = st.session_state.get("ruta_estructuras_compacto")

        if df_e is None or df_e.empty:
            st.warning("⚠️ Primero completa estructuras.")
        else:
            seccion_exportacion(
                df=df_e,
                modo_carga=st.session_state.get("modo_carga_seleccionado"),
                ruta_estructuras=ruta_e,
                ruta_datos_materiales=ruta_datos_materiales_por_defecto(),
            )

    elif seccion == "mapa_kml":
        seccion_mapa_kmz()
