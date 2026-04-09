# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import re
from typing import Any


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
# LIMPIEZA MTEXT
# =========================================================
def _limpiar_mtext(texto: str) -> str:

    if not texto:
        return ""

    texto = re.sub(r"\{.*?;", "", texto)
    texto = texto.replace("{", "").replace("}", "")
    texto = texto.replace("\\P", " ")

    texto = " ".join(texto.split())

    return texto.upper()


# =========================================================
# EXTRAER
# =========================================================
def _extraer(texto: str) -> list[str]:

    encontrados = []

    for p in PATRONES:
        encontrados += re.findall(p, texto, flags=re.IGNORECASE)

    return encontrados


# =========================================================
# NORMALIZAR
# =========================================================
def _norm(s: str) -> str:
    return (
        s.upper()
        .replace(" ", "-")
        .replace("--", "-")
        .strip("-")
    )


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================
def leer_dxf(archivo_dxf: Any) -> pd.DataFrame:
    """
    ✔ Devuelve DataFrame válido para dominio
    ✔ Columnas: Estructura, Cantidad
    ✔ Nunca devuelve None
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
    # PARSE DXF
    # =====================================================
    lineas = contenido.splitlines()

    layer_actual = None
    buffer_texto = ""

    estructuras = []

    for i in range(len(lineas) - 1):

        codigo = lineas[i].strip()
        valor = lineas[i + 1].strip()

        # capa
        if codigo == "8":
            layer_actual = valor.upper()

        # texto MTEXT / TEXT
        if codigo in ("1", "3"):

            if layer_actual and CAPA_OBJETIVO in layer_actual:

                buffer_texto += " " + valor

        # corte de entidad
        if codigo == "0" and buffer_texto:

            limpio = _limpiar_mtext(buffer_texto)

            encontrados = _extraer(limpio)

            if encontrados:
                estructuras.extend(encontrados)

            buffer_texto = ""

    # último bloque
    if buffer_texto:
        limpio = _limpiar_mtext(buffer_texto)
        estructuras.extend(_extraer(limpio))

    # =====================================================
    # VALIDACIÓN FUERTE (CONTRATO)
    # =====================================================
    if not estructuras:
        raise ValueError(
            "DXF válido pero no contiene estructuras reconocibles"
        )

    # =====================================================
    # NORMALIZACIÓN FINAL
    # =====================================================
    estructuras = [_norm(e) for e in estructuras if e]

    df = pd.DataFrame({
        "Estructura": estructuras
    })

    # ✔ GARANTÍA DE COLUMNA
    if "Estructura" not in df.columns:
        raise ValueError("Error interno: columna Estructura no creada")

    # =====================================================
    # AGRUPACIÓN
    # =====================================================
    df["Cantidad"] = 1

    df = (
        df.groupby("Estructura", as_index=False)["Cantidad"]
        .sum()
    )

    # =====================================================
    # VALIDACIÓN FINAL DEL CONTRATO
    # =====================================================
    columnas = set(df.columns)

    required = {"Estructura", "Cantidad"}

    if not required.issubset(columnas):
        raise ValueError(
            f"Salida inválida leer_dxf: columnas {columnas}"
        )

    if df.empty:
        raise ValueError("leer_dxf generó DataFrame vacío")

    return df
