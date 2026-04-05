# -*- coding: utf-8 -*-
# app.py

from __future__ import annotations
import os
import streamlit as st

from interfaz.orquestador_interfaz import ejecutar_orquestador_interfaz
from entradas.orquestador_entradas import cargar_entrada

# =========================================================
# NAVEGACIÓN
# =========================================================

SECCIONES = [
    ("datos", "Datos"),
    ("cables", "Cables"),
    ("modo", "Modo de Carga"),
    ("estructuras", "Estructuras"),
    ("materiales", "Materiales Extra"),
    ("final", "Finalizar"),
    ("exportar", "Exportación"),
    ("mapa_kml", "Mapa / KMZ"),
]


def _nav_estado_actual() -> str:
    qp = st.query_params.get("s")

    if isinstance(qp, list):
        qp = qp[0] if qp else None

    sec = qp or st.session_state.get("sec") or "datos"

    st.session_state["sec"] = sec

    return sec


def _ir_a(seccion: str) -> None:
    st.session_state["sec"] = seccion
    st.query_params["s"] = seccion
    st.rerun()


def _barra_nav_botones(seccion_activa: str) -> None:

    st.markdown(
        """
        <style>
        .nav-top { position: sticky; top: 0; z-index: 999; background: #fff; padding: .55rem 0 .6rem; border-bottom: 1px solid #e6e6e6; }
        .pill { display:inline-block; margin:.25rem .45rem .25rem 0; }
        .pill button {
            background:#0A3D91;
            color:#fff;
            border:1px solid #0A3D91;
            border-radius: 10px;
            padding:.45rem .85rem;
            font-weight:600;
            font-size:.92rem;
        }
        .pill.active button { background:#072C69; border-color:#072C69; }
        .stButton>button { min-width: 140px; }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<div class="nav-top">', unsafe_allow_html=True)

    cols = st.columns(len(SECCIONES), gap="small")

    for i, (key, label) in enumerate(SECCIONES):
        with cols[i]:
            active_cls = "active" if key == seccion_activa else ""
            st.markdown(f'<div class="pill {active_cls}">', unsafe_allow_html=True)

            if st.button(label, key=f"nav_{key}"):
                _ir_a(key)

            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# INICIALIZACIÓN GLOBAL
# =========================================================

def _init_rutas():
    base_dir = os.path.dirname(__file__)

    ruta = os.path.join(base_dir, "data", "Estructura_datos.xlsx")

    st.session_state.setdefault("ruta_datos_materiales", ruta)


def _init_estado_base():
    """
    Estado mínimo global (NO lógica de negocio)
    """

    defaults = {
        "datos_proyecto": {},
        "materiales_extra": [],
        "df_estructuras": None,
        "resultado_calculo": None,
        "pdfs_generados": None,
        "calculo_finalizado": False,
    }

    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


# =========================================================
# APP
# =========================================================

def main():

    st.set_page_config(
        page_title="Cálculo de Materiales",
        layout="wide"
    )

    _init_rutas()
    _init_estado_base()

    # =====================================================
    # HEADER
    # =====================================================
    st.title("⚡ Cálculo de Materiales de Redes")

    # =====================================================
    # MEMBRETE PDF
    # =====================================================
    st.radio(
        "Membrete del PDF",
        ["SMART", "ENEE", "SIN LOGO"],
        key="membrete_pdf",
        horizontal=True,
    )

    # =====================================================
    # ORQUESTADOR
    # =====================================================
    ejecutar_orquestador_interfaz(
        _nav_estado_actual,
        _barra_nav_botones,
    )


if __name__ == "__main__":
    main()
