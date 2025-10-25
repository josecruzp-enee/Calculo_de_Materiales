# -*- coding: utf-8 -*-
"""
formularios.py
Módulo de formularios para ingresar datos generales del proyecto.
• Diseño compacto (dos columnas)
• Persistencia verdadera en session_state
• Sin “Resumen de datos del proyecto” (se eliminó)

Autor: José Nikol Cruz
"""

from __future__ import annotations
import streamlit as st
from datetime import date, datetime


def _ensure_estado():
    """Asegura que exista el contenedor de datos en session_state (sin sobreescribir)."""
    st.session_state.setdefault("datos_proyecto", {})


def _mezclar_sin_vacios(actual: dict, nuevos: dict) -> dict:
    """
    Devuelve un dict mezclando 'actual' con 'nuevos' sin pisar con cadenas vacías.
    Mantiene los valores previos si el nuevo viene vacío.
    """
    limpio = {k: v for k, v in (nuevos or {}).items() if v not in ("", None)}
    return {**(actual or {}), **limpio}


def formulario_datos_proyecto() -> None:
    """Formulario compacto y persistente para los datos generales del proyecto."""
    _ensure_estado()
    dp = st.session_state.get("datos_proyecto", {}) or {}

    st.markdown("### 📘 Datos Generales del Proyecto")

    # Helpers para valores por defecto
    def _get(k: str, default=""):
        return dp.get(k, default)

    # Normalizar fecha guardada (si existiera como string)
    fi_raw = _get("fecha_informe", str(date.today()))
    try:
        fi_default = datetime.strptime(fi_raw, "%Y-%m-%d").date()
    except Exception:
        fi_default = date.today()

    # -------- Formulario (guarda sólo al submit) --------
    with st.form("form_datos_proyecto", clear_on_submit=False):
        col1, col2 = st.columns(2)

        with col1:
            nombre_proyecto = st.text_input(
                "📄 Nombre del Proyecto",
                value=_get("nombre_proyecto", ""),
                key="form_nombre_proyecto",
            )
            empresa = st.text_input(
                "🏢 Empresa / Área",
                value=_get("empresa", "ENEE"),
                key="form_empresa",
            )
            # selectbox con índice a partir del valor guardado
            opciones_tension = ["13.8", "34.5"]
            nivel_actual = _get("nivel_de_tension", "13.8")
            try:
                idx_tension = opciones_tension.index(nivel_actual)
            except ValueError:
                idx_tension = 0
            nivel_tension = st.selectbox(
                "⚡ Nivel de Tensión (kV)",
                opciones_tension,
                index=idx_tension,
                key="form_nivel_tension",
            )

        with col2:
            codigo_proyecto = st.text_input(
                "🔢 Código / Expediente",
                value=_get("codigo_proyecto", ""),
                key="form_codigo_proyecto",
            )
            responsable = st.text_input(
                "👷‍♂️ Responsable / Diseñador",
                value=_get("responsable", ""),
                key="form_responsable",
            )
            fecha_informe = st.date_input(
                "📅 Fecha del Informe",
                value=fi_default,
                key="form_fecha_informe",
            )

        guardar = st.form_submit_button("💾 Guardar datos", type="primary")

    # -------- Guardado controlado --------
    if guardar:
        nuevos = {
            "nombre_proyecto": (nombre_proyecto or "").strip(),
            "codigo_proyecto": (codigo_proyecto or "").strip(),
            "empresa": (empresa or "").strip(),
            "responsable": (responsable or "").strip(),
            "nivel_de_tension": nivel_tension,
            "fecha_informe": str(fecha_informe),
        }
        st.session_state["datos_proyecto"] = _mezclar_sin_vacios(dp, nuevos)
        st.success("✅ Datos del proyecto guardados correctamente.")


def mostrar_datos_formateados() -> None:
    """
    (Opcional) Muestra los datos guardados en formato compacto.
    Puedes llamarla donde quieras o no usarla.
    """
    _ensure_estado()
    dp = st.session_state.get("datos_proyecto", {}) or {}
    if not dp:
        return

    with st.expander("📄 Datos guardados (vista rápida)", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Nombre del Proyecto:** {dp.get('nombre_proyecto','')}")
            st.write(f"**Empresa / Área:** {dp.get('empresa','')}")
            st.write(f"**Nivel de Tensión (kV):** {dp.get('nivel_de_tension','')}")
        with col2:
            st.write(f"**Código / Expediente:** {dp.get('codigo_proyecto','')}")
            st.write(f"**Responsable / Diseñador:** {dp.get('responsable','')}")
            st.write(f"**Fecha del Informe:** {dp.get('fecha_informe','')}")
