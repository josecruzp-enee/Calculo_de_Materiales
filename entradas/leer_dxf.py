# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import re
from typing import Any
import streamlit as st


CAPA_OBJETIVO = "ESTRUCTURAS"

PATRONES = [
    r"A[-\s]?[IVX]+[-\s]?\d+[A-Z]?",
    r"B[-\s]?[IVX]+[-\s]?\d+[A-Z]?",
    r"PC[-\s]?\d+[A-Z]?",
    r"TS[-\s]?\d+\s?KVA",
    r"CT[-\s]?N",
    r"R[-\s]?\d+",
]


def _limpiar_texto(texto: str) -> str:
    if not texto:
        return ""

    texto = re.sub(r"\{.*?;", "", texto)
    texto = texto.replace("{", "").replace("}", "")
    texto = texto.replace("\\P", " ")
    texto = " ".join(texto.split())

    return texto.upper()


def _extraer_estructuras(texto: str) -> list[str]:
    encontrados = []

    for patron in PATRONES:
        encontrados.extend(re.findall(patron, texto, flags=re.IGNORECASE))

    return encontrados


def _normalizar(codigo: str) -> str:
    return (
        codigo.upper()
        .replace(" ", "-")
        .replace("--", "-")
        .strip("-")
    )


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================
def leer_dxf(archivo_dxf: Any) -> pd.DataFrame:

    debug = {
        "input": {
            "tipo": str(type(archivo_dxf))
        },
        "proceso": {},
        "output": {},
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
    # PARSEO
    # =====================================================
    lineas = contenido.splitlines()
    debug["proceso"]["total_lineas"] = len(lineas)

    layer_actual = ""
    buffer_texto = ""
    estructuras = []

    capas_detectadas = set()
    textos_capturados = []

    for i in range(len(lineas) - 1):

        codigo = lineas[i].strip()
        valor = lineas[i + 1].strip()

        if codigo == "8":
            layer_actual = valor.upper()
            capas_detectadas.add(layer_actual)

        if codigo in ("1", "3"):
            if CAPA_OBJETIVO in layer_actual:
                buffer_texto += " " + valor

        if codigo == "0" and buffer_texto:

            limpio = _limpiar_texto(buffer_texto)

            if limpio:
                textos_capturados.append(limpio[:200])

            encontrados = _extraer_estructuras(limpio)

            if encontrados:
                estructuras.extend(encontrados)

            buffer_texto = ""

    if buffer_texto:
        limpio = _limpiar_texto(buffer_texto)
        estructuras.extend(_extraer_estructuras(limpio))

    debug["proceso"]["capas_detectadas"] = list(capas_detectadas)
    debug["proceso"]["textos_capturados"] = textos_capturados[:10]
    debug["proceso"]["estructuras_detectadas"] = estructuras[:20]

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    if not estructuras:
        debug["estado"] = {
            "ok": False,
            "error": "No se detectaron estructuras"
        }
        _guardar_debug(debug)
        raise ValueError(
            "DXF leído pero no se encontraron estructuras en capa Estructuras"
        )

    # =====================================================
    # NORMALIZACIÓN
    # =====================================================
    estructuras = [_normalizar(e) for e in estructuras if e]

    df = pd.DataFrame({
        "Estructura": estructuras,
        "Cantidad": 1
    })

    df = df.groupby("Estructura", as_index=False)["Cantidad"].sum()

    # =====================================================
    # VALIDACIÓN FINAL
    # =====================================================
    if df.empty:
        debug["estado"] = {"ok": False, "error": "DataFrame vacío"}
        _guardar_debug(debug)
        raise ValueError("DataFrame vacío tras procesar DXF")

    if not {"Estructura", "Cantidad"}.issubset(df.columns):
        debug["estado"] = {"ok": False, "error": "Columnas inválidas"}
        _guardar_debug(debug)
        raise ValueError("Columnas inválidas en salida DXF")

    # =====================================================
    # OUTPUT
    # =====================================================
    debug["output"] = {
        "filas": len(df),
        "columnas": list(df.columns)
    }

    debug["estado"] = {"ok": True}

    _guardar_debug(debug)

    return df


# =========================================================
# GUARDAR DEBUG
# =========================================================
def _guardar_debug(debug: dict):
    st.session_state.setdefault("debug_pipeline", {})
    st.session_state["debug_pipeline"]["DXF"] = debug
