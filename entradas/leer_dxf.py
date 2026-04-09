# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import re
from typing import Any


# =========================================================
# CONFIG
# =========================================================
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
# LIMPIAR TEXTO DXF (MTEXT/TEXT)
# =========================================================
def _limpiar_texto(texto: str) -> str:
    if not texto:
        return ""

    # quitar formato tipo {\C7; ... }
    texto = re.sub(r"\{.*?;", "", texto)

    # quitar llaves
    texto = texto.replace("{", "").replace("}", "")

    # saltos de línea DXF
    texto = texto.replace("\\P", " ")

    # limpiar espacios
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
def leer_dxf(archivo_dxf: Any) -> pd.DataFrame:
    """
    Lector DXF robusto para estructuras.

    ✔ Filtra por capa "Estructuras"
    ✔ Soporta TEXT y MTEXT
    ✔ Devuelve DataFrame válido
    ✔ Columnas: Estructura, Cantidad
    ✔ Lanza excepción si falla
    """

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
    # PARSEO DXF
    # =====================================================
    lineas = contenido.splitlines()

    layer_actual = ""
    buffer_texto = ""

    estructuras = []

    for i in range(len(lineas) - 1):

        codigo = lineas[i].strip()
        valor = lineas[i + 1].strip()

        # capa (group code 8)
        if codigo == "8":
            layer_actual = valor.upper()

        # texto (TEXT / MTEXT)
        if codigo in ("1", "3"):

            if CAPA_OBJETIVO in layer_actual:
                buffer_texto += " " + valor

        # fin de entidad
        if codigo == "0" and buffer_texto:

            limpio = _limpiar_texto(buffer_texto)

            encontrados = _extraer_estructuras(limpio)

            if encontrados:
                estructuras.extend(encontrados)

            buffer_texto = ""

    # procesar último bloque
    if buffer_texto:
        limpio = _limpiar_texto(buffer_texto)
        estructuras.extend(_extraer_estructuras(limpio))

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    if not estructuras:
        raise ValueError(
            "DXF leído pero no se encontraron estructuras en capa Estructuras"
        )

    # =====================================================
    # NORMALIZACIÓN FINAL
    # =====================================================
    estructuras = [_normalizar(e) for e in estructuras if e]

    df = pd.DataFrame({
        "Estructura": estructuras,
        "Cantidad": 1
    })

    # agrupar
    df = (
        df.groupby("Estructura", as_index=False)["Cantidad"]
        .sum()
    )

    # =====================================================
    # VALIDACIÓN DE CONTRATO
    # =====================================================
    if df.empty:
        raise ValueError("DataFrame vacío tras procesar DXF")

    if not {"Estructura", "Cantidad"}.issubset(df.columns):
        raise ValueError("Columnas inválidas en salida DXF")

    return df
