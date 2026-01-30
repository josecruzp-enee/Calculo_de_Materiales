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

    # Navegación
    seccion = _nav_estado_actual()
    _barra_nav_botones(seccion)

    # Render condicional
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

        st.write("DEBUG df_estructuras:", None if df_estructuras is None else df_estructuras.shape)

        if df_estructuras is not None and hasattr(df_estructuras, "empty") and not df_estructuras.empty:
            # Alias viejo (para no romper tu flujo actual)
            st.session_state["df_estructuras_compacto"] = df_estructuras
            st.session_state["ruta_estructuras_compacto"] = ruta_estructuras

            # Paquete estándar (nuevo)
            st.session_state["df_estructuras"] = df_estructuras
            st.session_state.setdefault("datos_proyecto", {})
            st.session_state.setdefault(
                "df_cables",
                pd.DataFrame(columns=["Tipo", "Configuración", "Calibre", "Longitud (m)"]),
            )
            st.session_state.setdefault(
                "df_materiales_extra",
                pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"]),
            )

            st.success("✅ Guardado en memoria. Ya puedes ir a Finalizar.")
        else:
            df_prev = st.session_state.get("df_estructuras_compacto")
            if df_prev is not None and hasattr(df_prev, "empty") and not df_prev.empty:
                st.info("ℹ️ No hubo nuevas estructuras, pero ya hay datos guardados previamente.")
            else:
                st.warning("⚠️ No se generó la tabla LARGA (compacta). No hay nada para Finalizar.")

    elif seccion == "materiales":
        seccion_adicionar_material()

    elif seccion == "final":
        df_e = st.session_state.get("df_estructuras")
        if df_e is None:
            df_e = st.session_state.get("df_estructuras_compacto")

        if df_e is None or not hasattr(df_e, "empty") or df_e.empty:
            st.info("⚠️ Carga primero las estructuras en la sección ‘Estructuras’.")
        else:
            seccion_finalizar_calculo(df_e)

    elif seccion == "exportar":
        df_e = st.session_state.get("df_estructuras")
        if df_e is None:
            df_e = st.session_state.get("df_estructuras_compacto")

        ruta_e = st.session_state.get("ruta_estructuras_compacto")

        if df_e is None or not hasattr(df_e, "empty") or df_e.empty:
            st.warning("⚠️ Primero completa la sección ‘Estructuras’ antes de exportar.")
            st.info("Ve a la pestaña **Estructuras**, carga o genera tus datos, y luego vuelve aquí.")
        else:
            st.markdown("### 🧩 DEBUG: DataFrame antes de exportar")
            st.write("Columnas:", df_e.columns.tolist())
            st.write("Shape:", df_e.shape)
            st.dataframe(df_e.head(10), use_container_width=True, hide_index=True)

            seccion_exportacion(
                df=df_e,
                modo_carga=st.session_state.get("modo_carga_seleccionado"),
                ruta_estructuras=ruta_e,
                ruta_datos_materiales=ruta_datos_materiales_por_defecto(),
            )

    elif seccion == "mapa_kml":
        seccion_mapa_kmz()


if __name__ == "__main__":
    main()
