# -*- coding: utf-8 -*-
"""
Selección de calibres de conductores (sin lectura desde Excel)
Autor: José Nikol Cruz
"""

import streamlit as st

def seleccionar_calibres_formulario(datos_proyecto=None):
    """Formulario interactivo para seleccionar calibres comerciales."""

    # === Calibres por defecto ===
    calibres = {
        "primario": ["2 ASCR", "1/0 ASCR", "2/0 ASCR", "3/0 ASCR", "4/0 ASCR", "266.8 MCM", "477 MCM", "556.5 MCM"],
        "secundario": ["2 WP", "1/0 WP", "2/0 WP", "3/0 WP", "4/0 WP", "266.8 WP"],
        "neutro": ["2 ASCR", "1/0 ASCR", "2/0 ASCR", "3/0 ASCR", "4/0 ASCR", "266.8 MCM"],
        "piloto": ["2 WP", "4 WP", "6 WP"],
        "retenidas": ["1/4 Acerado", "5/8 Acerado", "3/4 Acerado"]
    }

    def combo_comercial(etiqueta, lista_opciones, valor_actual="", clave=""):
        index = lista_opciones.index(valor_actual) if valor_actual in lista_opciones else 0
        return st.selectbox(etiqueta, lista_opciones, index=index, key=f"select_{clave}")

    st.markdown("### 2️⃣ Selección de Calibres de Conductores")

    col1, col2 = st.columns(2)

    with col1:
        calibre_primario = combo_comercial(
            "⚡ Calibre del Conductor de Media Tensión",
            calibres["primario"],
            (datos_proyecto or {}).get("calibre_primario", ""),
            clave="primario"
        )

        calibre_neutro = combo_comercial(
            "🧵 Calibre del Conductor de Neutro",
            calibres["neutro"],
            (datos_proyecto or {}).get("calibre_neutro", ""),
            clave="neutro"
        )

        calibre_retenidas = combo_comercial(
            "🪜 Calibre del Cable de Retenida",
            calibres["retenidas"],
            (datos_proyecto or {}).get("calibre_retenidas", ""),
            clave="retenidas"
        )

    with col2:
        calibre_secundario = combo_comercial(
            "🔌 Calibre del Conductor de Baja Tensión",
            calibres["secundario"],
            (datos_proyecto or {}).get("calibre_secundario", ""),
            clave="secundario"
        )

        calibre_piloto = combo_comercial(
            "📡 Calibre del Hilo Piloto",
            calibres["piloto"],
            (datos_proyecto or {}).get("calibre_piloto", ""),
            clave="piloto"
        )

    return {
        "calibre_primario": calibre_primario,
        "calibre_secundario": calibre_secundario,
        "calibre_neutro": calibre_neutro,
        "calibre_piloto": calibre_piloto,
        "calibre_retenidas": calibre_retenidas
    }
