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
# LIMPIEZA TEXTO MTEXT
# =========================================================
def _limpiar_mtext(texto: str) -> str:

    if not texto:
        return ""

    # quitar formato { \C7; ... }
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

        # MTEXT / TEXT
        if codigo in ("1", "3"):

            if layer_actual and CAPA_OBJETIVO in layer_actual:

                buffer_texto += " " + valor

        # corte de entidad (cuando cambia código)
        if codigo == "0" and buffer_texto:

            limpio = _limpiar_mtext(buffer_texto)

            encontrados = _extraer(limpio)

            if encontrados:
                estructuras.extend(encontrados)

            buffer_texto = ""

    # último buffer
    if buffer_texto:
        limpio = _limpiar_mtext(buffer_texto)
        estructuras.extend(_extraer(limpio))

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    if not estructuras:
        raise ValueError(
            "DXF leído pero no se encontraron estructuras válidas en capa Estructuras"
        )

    estructuras = [_norm(e) for e in estructuras]

    df = pd.DataFrame({"Estructura": estructuras})
    df["Cantidad"] = 1

    df = (
        df.groupby("Estructura", as_index=False)["Cantidad"]
        .sum()
        .sort_values("Estructura")
    )

    return df
