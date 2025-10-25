# app.py
# -*- coding: utf-8 -*-
import streamlit as st

from interfaz.base import (
    renderizar_encabezado,
    inicializar_estado,
    seleccionar_modo_carga,
    ruta_datos_materiales_por_defecto,
)

from interfaz.datos_proyecto import seccion_datos_proyecto
from interfaz.cables import seccion_cables_proyecto
from interfaz.estructuras import seccion_entrada_estructuras
from interfaz.materiales_extra import seccion_adicionar_material
from interfaz.exportacion import seccion_finalizar_calculo, seccion_exportacion


SECCIONES = [
    "1) Datos del Proyecto",
    "2) Configuración de Cables",
    "3) Modo de Carga",
    "4) Estructuras del Proyecto",
    "5) Finalizar Cálculo",
    "6) Exportación",
]


def _init_router():
    """Inicializa variables de navegación y estado mínimo requerido."""
    if "step" not in st.session_state:
        st.session_state.step = 0
    # buffers de datos para pasos siguientes
    st.session_state.setdefault("modo_carga", None)
    st.session_state.setdefault("df_estructuras", None)
    st.session_state.setdefault("ruta_estructuras", None)


def _router_ui():
    """Radio lateral + botones stepper (anterior / siguiente)."""
    sel = st.sidebar.radio("Navegación", SECCIONES, index=st.session_state.step)

    # Sincroniza radio -> step
    st.session_state.step = SECCIONES.index(sel)

    col_prev, col_info, col_next = st.columns([1, 6, 1])
    with col_prev:
        if st.button("⬅️ Anterior", use_container_width=True, disabled=st.session_state.step == 0):
            st.session_state.step = max(0, st.session_state.step - 1)
    with col_info:
        st.write(f"**{SECCIONES[st.session_state.step]}**")
    with col_next:
        if st.button(
            "Siguiente ➡️",
            use_container_width=True,
            disabled=st.session_state.step == len(SECCIONES) - 1,
        ):
            st.session_state.step = min(len(SECCIONES) - 1, st.session_state.step + 1)

    st.markdown("---")
    return SECCIONES[st.session_state.step]


def main() -> None:
    # 0) Encabezado + estado base
    renderizar_encabezado()
    inicializar_estado()
    _init_router()

    # Router (sin scroll: una sección a la vez)
    seleccion = _router_ui()

    # 1) Datos generales
    if seleccion == "1) Datos del Proyecto":
        seccion_datos_proyecto()

    # 2) Cables
    elif seleccion == "2) Configuración de Cables":
        seccion_cables_proyecto()

    # 3) Selección de modo de carga
    elif seleccion == "3) Modo de Carga":
        modo = seleccionar_modo_carga()
        st.session_state["modo_carga"] = modo  # persistir para el siguiente paso

    # 4) Estructuras (usa el modo seleccionado)
    elif seleccion == "4) Estructuras del Proyecto":
        modo = st.session_state.get("modo_carga")
        if not modo:
            st.warning("Seleccioná primero el **Modo de Carga** en la sección anterior.")
            return

        df_estructuras, ruta_estructuras = seccion_entrada_estructuras(modo)
        # persistir resultados para pasos 5 y 6
        st.session_state["df_estructuras"] = df_estructuras
        st.session_state["ruta_estructuras"] = ruta_estructuras

    # 5) Finalizar cálculo (usa df_estructuras)
    elif seleccion == "5) Finalizar Cálculo":
        df_estructuras = st.session_state.get("df_estructuras")
        if df_estructuras is None:
            st.warning("Ingresá primero las **Estructuras del Proyecto**.")
            return
        seccion_finalizar_calculo(df_estructuras)

    # 6) Exportación (usa todo lo previo)
    elif seleccion == "6) Exportación":
        df_estructuras = st.session_state.get("df_estructuras")
        modo = st.session_state.get("modo_carga")
        ruta_estructuras = st.session_state.get("ruta_estructuras")

        if df_estructuras is None or modo is None:
            st.warning("Falta información previa: completá las secciones anteriores.")
            return

        seccion_exportacion(
            df=df_estructuras,
            modo_carga=modo,
            ruta_estructuras=ruta_estructuras,
            ruta_datos_materiales=ruta_datos_materiales_por_defecto(),
        )


if __name__ == "__main__":
    main()
