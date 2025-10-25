# app.py — versión compacta en una sola pantalla (anclas + barra fija)
# -*- coding: utf-8 -*-

import streamlit as st

# ==== Importa tus secciones existentes ====
from interfaz.base import (
    renderizar_encabezado,
    inicializar_estado,
    seleccionar_modo_carga,           # crea el radio UNA sola vez
    ruta_datos_materiales_por_defecto,
)
from interfaz.datos_proyecto import seccion_datos_proyecto
from interfaz.cables import seccion_cables_proyecto
from interfaz.estructuras import seccion_entrada_estructuras
from interfaz.materiales_extra import seccion_adicionar_material
from interfaz.exportacion import seccion_finalizar_calculo, seccion_exportacion


# =========================
#  Estilos compactos + barra fija
# =========================
def _css_compacto():
    st.markdown(
        """
        <style>
        .block-container { padding-top: .5rem !important; padding-bottom: .5rem !important; max-width: 1300px; }
        h1,h2,h3 { margin: .3rem 0 .2rem 0 !important; }
        [data-testid="stVerticalBlock"] { gap: .4rem !important; }
        .stButton>button { padding: .35rem .7rem !important; border-radius: 6px !important; }
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
            height: 34px !important; font-size: .92rem !important; background: #f7f9fc !important;
        }
        .nav-stick { position: sticky; top: 0; z-index: 999; background: white; padding: .4rem .6rem; margin: 0 0 .6rem 0; border-bottom: 1px solid #e6e6e6; }
        .nav-stick .btn { display:inline-block; margin: 2px 6px 2px 0; padding: .35rem .6rem; background:#004080; color:#fff; border-radius:8px; font-size:.85rem; font-weight:600; text-decoration:none; }
        .nav-stick .btn:hover { background:#0066cc; }
        .anchor-gap { scroll-margin-top: 70px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

def _barra_nav():
    st.markdown(
        """
        <div class="nav-stick">
          <a class="btn" href="#datos">Datos</a>
          <a class="btn" href="#cables">Cables</a>
          <a class="btn" href="#modo">Modo de Carga</a>
          <a class="btn" href="#estructuras">Estructuras</a>
          <a class="btn" href="#materiales">Adicionar Material</a>
          <a class="btn" href="#final">Finalizar</a>
          <a class="btn" href="#exportar">Exportación</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================
#  App compacta (una sola pantalla)
# =========================
def main() -> None:
    st.set_page_config(page_title="Cálculo de Materiales", layout="wide")
    renderizar_encabezado()
    inicializar_estado()
    _css_compacto()
    _barra_nav()

    # 1) Datos del proyecto
    st.markdown('<div id="datos" class="anchor-gap"></div>', unsafe_allow_html=True)
    seccion_datos_proyecto()
    st.markdown("---")

    # 2) Cables
    st.markdown('<div id="cables" class="anchor-gap"></div>', unsafe_allow_html=True)
    seccion_cables_proyecto()
    st.markdown("---")

    # 3) Modo de carga — CREA EL RADIO SOLO AQUÍ
    st.markdown('<div id="modo" class="anchor-gap"></div>', unsafe_allow_html=True)
    st.subheader("3) Modo de Carga")
    modo = seleccionar_modo_carga()  # usa key="modo_carga_radio" internamente (una única vez)
    st.session_state["modo_carga_seleccionado"] = modo
    st.markdown("---")

    # 4) Estructuras — lee el valor ya elegido (no vuelvas a crear el radio)
    st.markdown('<div id="estructuras" class="anchor-gap"></div>', unsafe_allow_html=True)
    modo = st.session_state.get("modo_carga_seleccionado", "Listas desplegables")
    df_estructuras, ruta_estructuras = seccion_entrada_estructuras(modo)
    st.session_state["df_estructuras_compacto"] = df_estructuras
    st.session_state["ruta_estructuras_compacto"] = ruta_estructuras
    st.markdown("---")

    # 5) Materiales extra
    st.markdown('<div id="materiales" class="anchor-gap"></div>', unsafe_allow_html=True)
    seccion_adicionar_material()
    st.markdown("---")

    # 6) Finalizar
    st.markdown('<div id="final" class="anchor-gap"></div>', unsafe_allow_html=True)
    df_e = st.session_state.get("df_estructuras_compacto")
    if df_e is None:
        st.info("Carga primero las estructuras en la sección anterior.")
    else:
        seccion_finalizar_calculo(df_e)
    st.markdown("---")

    # 7) Exportación
    st.markdown('<div id="exportar" class="anchor-gap"></div>', unsafe_allow_html=True)
    df_e = st.session_state.get("df_estructuras_compacto")
    ruta_e = st.session_state.get("ruta_estructuras_compacto")
    seccion_exportacion(
        df=df_e,
        modo_carga=st.session_state.get("modo_carga_seleccionado"),
        ruta_estructuras=ruta_e,
        ruta_datos_materiales=ruta_datos_materiales_por_defecto(),
    )

if __name__ == "__main__":
    main()
