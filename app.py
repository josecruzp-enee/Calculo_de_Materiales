# app.py — navegación por secciones sin scroll (estado + query params)
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import pandas as pd
import streamlit as st

# ==== Importa tus secciones ya existentes ====
from interfaz.base import (
    renderizar_encabezado,
    inicializar_estado,
    seleccionar_modo_carga,           # crea el radio SOLO aquí
    ruta_datos_materiales_por_defecto,
)
from interfaz.datos_proyecto import seccion_datos_proyecto
from interfaz.cables import seccion_cables_proyecto
from interfaz.estructuras import seccion_entrada_estructuras
from interfaz.materiales_extra import seccion_adicionar_material
from interfaz.exportacion import seccion_finalizar_calculo, seccion_exportacion
from interfaz.mapa_kml import seccion_mapa_kmz
from interfaz.orquestador_interfaz import ejecutar_orquestador_interfaz

# ---------------------------
#   Navegación sin scroll
# ---------------------------
SECCIONES = [
    ("datos", "Datos"),
    ("cables", "Cables"),
    ("modo", "Modo de Carga"),
    ("estructuras", "Estructuras"),
    ("materiales", "Adicionar Material"),
    ("final", "Finalizar"),
    ("exportar", "Exportación"),
    ("mapa_kml", "Mapa / KMZ"),
]


def _nav_estado_actual() -> str:
    """Lee la sección actual desde query params o estado; pone un valor por defecto."""
    qp = st.query_params.get("s")
    if isinstance(qp, list):
        qp = qp[0] if qp else None
    sec = qp or st.session_state.get("sec") or "datos"
    st.session_state["sec"] = sec
    return sec


def _ir_a(seccion: str) -> None:
    """Cambia de sección y re-ejecuta."""
    st.session_state["sec"] = seccion
    st.query_params["s"] = seccion
    st.rerun()


def _barra_nav_botones(seccion_activa: str) -> None:
    """Barra superior con botones."""
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
            box-shadow: 0 1px 0 rgba(0,0,0,.05);
        }
        .pill button:hover { background:#145CC9; border-color:#145CC9; }
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


def _init_rutas() -> None:
    """Define rutas base (solo una vez)."""
    base_dir = os.path.dirname(__file__)
    ruta_datos_materiales = os.path.join(base_dir, "data", "Estructura_datos.xlsx")
    st.session_state.setdefault("ruta_datos_materiales", ruta_datos_materiales)


# ---------------------------
#           App
# ---------------------------
def main() -> None:
    st.set_page_config(page_title="Cálculo de Materiales", layout="wide")

    _init_rutas()

    # Encabezado / estado global
    renderizar_encabezado()
    inicializar_estado()

    # ---------------------------
    #   Selector de membrete PDF
    # ---------------------------
    if "membrete_pdf" not in st.session_state:
        st.session_state["membrete_pdf"] = "SMART"

    st.radio(
        "Membrete del PDF",
        ["SMART", "ENEE", "SIN LOGO"],
        key="membrete_pdf",
        horizontal=True,
    )

    # ============================
    # 🔥 ORQUESTADOR UI (NUEVO)
    # ============================
    ejecutar_orquestador_interfaz(
        _nav_estado_actual,
        _barra_nav_botones,
    )

if __name__ == "__main__":
    main()


