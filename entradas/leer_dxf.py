# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import re
from typing import Any, Tuple


CAPA_OBJETIVO = "ESTRUCTURAS"


PATRONES = [
    r"A[-\s]?[IVX]+[-\s]?\d+[A-Z]?",
    r"B[-\s]?[IVX]+[-\s]?\d+[A-Z]?",
    r"PC[-\s]?\d+[A-Z]?",
    r"TS[-\s]?\d+\s?KVA",
    r"CT[-\s]?N",
    r"R[-\s]?\d+",
]


# =========================================================
# LIMPIAR TEXTO DXF
# =========================================================
def _limpiar_texto(texto: str) -> str:
    if not texto:
        return ""

    texto = re.sub(r"\{.*?;", "", texto)
    texto = texto.replace("{", "").replace("}", "")
    texto = texto.replace("\\P", " ")
    texto = " ".join(texto.split())

    return texto.upper()


# =========================================================
# EXTRAER ESTRUCTURAS
# =========================================================
def _extraer_estructuras(texto: str) -> list[str]:
    encontrados = []

    for patron in PATRONES:
        encontrados.extend(re.findall(patron, texto, flags=re.IGNORECASE))

    return encontrados


# =========================================================
# NORMALIZAR
# =========================================================
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
def leer_dxf(archivo_dxf: Any) -> Tuple[pd.DataFrame, dict]:
    """
    ✔ Devuelve: df + debug
    ✔ No rompe contrato (puedes ignorar debug si no lo usas)
    """

    debug = {
        "capas_detectadas": set(),
        "textos_capturados": [],
        "estructuras_detectadas": [],
        "total_lineas": 0,
    }

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    if archivo_dxf is None:
        raise ValueError("archivo_dxf es None")

    try:
        if hasattr(archivo_dxf, "seek"):
            archivo_dxf.seek(0)

        raw = archivo_dxf.read()

        if not raw:
            raise ValueError("DXF vacío")

        contenido = raw.decode("latin-1", errors="ignore")

    except Exception as e:
        raise ValueError(f"No se pudo leer DXF: {e}")

    # =====================================================
    # PARSEO
    # =====================================================
    lineas = contenido.splitlines()
    debug["total_lineas"] = len(lineas)

    layer_actual = ""
    buffer_texto = ""
    estructuras = []

    for i in range(len(lineas) - 1):

        codigo = lineas[i].strip()
        valor = lineas[i + 1].strip()

        # CAPA
        if codigo == "8":
            layer_actual = valor.upper()
            debug["capas_detectadas"].add(layer_actual)

        # TEXTO
        if codigo in ("1", "3"):
            if CAPA_OBJETIVO in layer_actual:
                buffer_texto += " " + valor

        # FIN ENTIDAD
        if codigo == "0" and buffer_texto:

            limpio = _limpiar_texto(buffer_texto)

            if limpio:
                debug["textos_capturados"].append(limpio[:200])

            encontrados = _extraer_estructuras(limpio)

            if encontrados:
                estructuras.extend(encontrados)
                debug["estructuras_detectadas"].extend(encontrados)

            buffer_texto = ""

    # último bloque
    if buffer_texto:
        limpio = _limpiar_texto(buffer_texto)
        estructuras.extend(_extraer_estructuras(limpio))

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    if not estructuras:
        debug["error"] = "No se detectaron estructuras"
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

    if df.empty:
        raise ValueError("DataFrame vacío tras procesar DXF")

    if not {"Estructura", "Cantidad"}.issubset(df.columns):
        raise ValueError("Columnas inválidas en salida DXF")

    return df, debug
