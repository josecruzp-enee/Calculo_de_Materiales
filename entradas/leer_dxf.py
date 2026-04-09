# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any
import pandas as pd
import streamlit as st


CAPA_OBJETIVO = "ESTRUCTURAS"


def leer_dxf(archivo_dxf: Any) -> pd.DataFrame:
    """
    Lector DXF (modo crudo)

    ✔ SOLO extrae texto desde la capa objetivo
    ✔ NO interpreta estructuras
    ✔ NO normaliza
    ✔ NO valida

    OUTPUT:
        DataFrame con columna:
            - texto (str)
    """

    debug = {
        "input": {"tipo": str(type(archivo_dxf))},
        "proceso": {},
        "estado": {}
    }

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    if archivo_dxf is None:
        debug["estado"] = {"ok": False, "error": "archivo_dxf es None"}
        _guardar_debug(debug)
        raise ValueError("archivo_dxf es None")

    try:
        if hasattr(archivo_dxf, "seek"):
            archivo_dxf.seek(0)

        raw = archivo_dxf.read()

        if not raw:
            raise ValueError("DXF vacío")

        contenido = raw.decode("latin-1", errors="ignore")

    except Exception as e:
        debug["estado"] = {"ok": False, "error": str(e)}
        _guardar_debug(debug)
        raise ValueError(f"No se pudo leer DXF: {e}")

    # =====================================================
    # PARSEO (SOLO TEXTO)
    # =====================================================
    lineas = contenido.splitlines()

    layer_actual = ""
    buffer_texto = []
    textos = []

    capas_detectadas = set()

    for i in range(len(lineas) - 1):

        codigo = lineas[i].strip()
        valor = lineas[i + 1].strip()

        # Detectar capa
        if codigo == "8":
            layer_actual = valor.upper()
            capas_detectadas.add(layer_actual)

        # Capturar texto solo en capa objetivo
        if codigo in ("1", "3") and CAPA_OBJETIVO in layer_actual:
            buffer_texto.append(valor)

        # Fin de entidad
        if codigo == "0" and buffer_texto:
            texto_unido = " ".join(buffer_texto).strip()

            if texto_unido:
                textos.append(texto_unido)

            buffer_texto = []

    # último bloque
    if buffer_texto:
        texto_unido = " ".join(buffer_texto).strip()
        if texto_unido:
            textos.append(texto_unido)

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    if not textos:
        debug["estado"] = {
            "ok": False,
            "error": "No se encontraron textos en capa ESTRUCTURAS"
        }
        _guardar_debug(debug)
        raise ValueError("DXF sin textos en capa ESTRUCTURAS")

    # =====================================================
    # OUTPUT
    # =====================================================
    df = pd.DataFrame({
        "texto": textos
    })

    # =====================================================
    # DEBUG
    # =====================================================
    debug["proceso"] = {
        "total_lineas": len(lineas),
        "capas_detectadas": list(capas_detectadas),
        "total_textos": len(textos),
        "preview_textos": textos[:10]
    }

    debug["output"] = {
        "filas": len(df),
        "columnas": list(df.columns)
    }

    debug["estado"] = {"ok": True}

    _guardar_debug(debug)

    return df


# =========================================================
# DEBUG STORAGE
# =========================================================
def _guardar_debug(debug: dict):
    st.session_state.setdefault("debug_pipeline", {})
    st.session_state["debug_pipeline"]["DXF"] = debug
