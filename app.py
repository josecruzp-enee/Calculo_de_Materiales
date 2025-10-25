## app.py  (versión compacta, una sola pantalla)
# -*- coding: utf-8 -*-

import streamlit as st

# ==== Importa tus secciones existentes (sin cambios) ====
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


# =========================
#  Estilos compactos + barra fija
# =========================
def _css_compacto():
    st.markdown(
        """
        <style>
        /* Contenedor más denso */
        .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 0.5rem !important;
            max-width: 1300px;
        }
        h1,h2,h3 { margin: .3rem 0 .2rem 0 !important; }
        [data-testid="stVerticalBlock"] { gap: .4rem !important; }
        .stButton>button { padding: .35rem .7rem !important; border-radius: 6px !important; }
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
            height: 34px !important; font-size: 0.92rem !important;
            background: #f7f9fc !important;
        }
        /* Tabs más delgadas */
        .stTabs [data-baseweb="tab"] { padding: 6px 10px !important; }
        /* Barra fija superior de navegación local */
        .nav-stick {
            position: sticky; top: 0; z-index: 999;
            background: white; padding: .4rem .6rem; margin: 0 0 .6rem 0;
            border-bottom: 1px solid #e6e6e6;
        }
        .nav-stick .btn {
            display:inline-block; margin: 2px 6px 2px 0; padding: .35rem .6rem;
            background:#004080; color:#fff; border-radius:8px; font-size:.85rem; font-weight:600;
            text-decoration:none;
        }
        .nav-stick .btn:hover { background:#0066cc; }
        /* Secciones ancla: pequeño margen para que no quede tapado por la barra */
        .anchor-gap { scroll-margin-top: 70px; }
        /* Oculta el “indice” rojo de radio en sidebar */
        .stRadio [role="radiogroup"] div { gap: .35rem !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _barra_nav():
    st.markdown(
        """
        <div class="nav-stick">
          <a class="btn" href="#datos"    >Datos</a>
          <a class="btn" href="#cables"   >Cables</a>
          <a class="btn" href="#modo"     >Modo de Carga</a>
          <a class="btn" href="#estructuras">Estructuras</a>
          <a class="btn" href="#materiales">Adicionar Material</a>
          <a class="btn" href="#final">Finalizar</a>
          <a class="btn" href="#exportar">Exportación</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================
#  App compacta (una pantalla)
# =========================
def main() -> None:
    renderizar_encabezado()
    inicializar_estado()
    _css_compacto()
    _barra_nav()

    # Tabs (todo en una sola pantalla, sin “siguiente/anterior”)
    tabs = st.tabs([
        "1) Datos", "2) Cables", "3) Modo de Carga",
        "4) Estructuras", "5) Materiales", "6) Finalizar", "7) Exportación"
    ])

    # 1) Datos del proyecto
    with tabs[0]:
        st.markdown('<div id="datos" class="anchor-gap"></div>', unsafe_allow_html=True)
        seccion_datos_proyecto()

    # 2) Cables (usa tu sección actual; ya dibuja su propio título interno)
    with tabs[1]:
        st.markdown('<div id="cables" class="anchor-gap"></div>', unsafe_allow_html=True)
        seccion_cables_proyecto()

    # 3) Modo de carga (mantiene tu selector actual, solo embebido)
    with tabs[2]:
        st.markdown('<div id="modo" class="anchor-gap"></div>', unsafe_allow_html=True)
        st.subheader("3) Modo de Carga")
        modo = seleccionar_modo_carga()
        # guardamos en estado por si otras secciones lo usan
        st.session_state["modo_carga_seleccionado"] = modo

    # 4) Estructuras
    with tabs[3]:
        st.markdown('<div id="estructuras" class="anchor-gap"></div>', unsafe_allow_html=True)
        modo = st.session_state.get("modo_carga_seleccionado", seleccionar_modo_carga())
        df_estructuras, ruta_estructuras = seccion_entrada_estructuras(modo)
        # Persistimos para usar en Finalizar y Exportar
        st.session_state["df_estructuras_compacto"] = df_estructuras
        st.session_state["ruta_estructuras_compacto"] = ruta_estructuras

    # 5) Materiales extra
    with tabs[4]:
        st.markdown('<div id="materiales" class="anchor-gap"></div>', unsafe_allow_html=True)
        seccion_adicionar_material()

    # 6) Finalizar
    with tabs[5]:
        st.markdown('<div id="final" class="anchor-gap"></div>', unsafe_allow_html=True)
        df_e = st.session_state.get("df_estructuras_compacto")
        if df_e is None:
            st.info("Carga primero las estructuras en la pestaña 4).")
        else:
            seccion_finalizar_calculo(df_e)

    # 7) Exportación
    with tabs[6]:
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
