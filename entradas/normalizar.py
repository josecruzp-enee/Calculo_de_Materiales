# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import re
from typing import Any, List, Dict


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================
def leer_dxf(archivo_dxf: Any) -> pd.DataFrame:
    """
    Lector DXF robusto alineado a contrato dominio entradas.

    ✔ Devuelve DataFrame limpio
    ✔ 1 fila = 1 estructura
    ✔ Columnas estándar: Punto, Estructura
    ✔ Filtra capa ESTRUCT*
    ✔ Limpieza fuerte
    ✔ Maneja múltiples estructuras en un MTEXT
    ✔ Falla explícita si no hay datos válidos
    """

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    if archivo_dxf is None:
        raise ValueError("archivo_dxf es None")

    # =====================================================
    # LECTURA SEGURA
    # =====================================================
    try:
        if hasattr(archivo_dxf, "seek"):
            archivo_dxf.seek(0)

        raw = archivo_dxf.read()

        if not raw:
            raise ValueError("DXF vacío o ya fue consumido")

        contenido = raw.decode("latin-1", errors="ignore")

    except Exception as e:
        raise ValueError(f"No se pudo leer el DXF: {e}")

    # =====================================================
    # TOKENIZACIÓN
    # =====================================================
    lineas = [l.strip() for l in contenido.splitlines() if l.strip()]

    resultados: List[Dict[str, str]] = []
    punto = 1

    capa_actual = None
    dentro_mtext = False
    buffer_texto: List[str] = []

    it = iter(lineas)

    try:
        for codigo in it:
            valor = next(it)

            codigo = codigo.strip()
            valor = valor.strip()

            # -------------------------------------------------
            # CAPA
            # -------------------------------------------------
            if codigo == "8":
                capa_actual = valor.upper().strip()

            # -------------------------------------------------
            # INICIO MTEXT
            # -------------------------------------------------
            if codigo == "0" and valor == "MTEXT":
                dentro_mtext = True
                buffer_texto = []
                continue

            # -------------------------------------------------
            # FIN MTEXT
            # -------------------------------------------------
            if dentro_mtext and codigo == "0":

                if not capa_actual or "ESTRUCT" not in capa_actual:
                    dentro_mtext = False
                    buffer_texto = []
                    continue

                texto = ",".join(buffer_texto)
                texto = _limpiar_texto(texto)

                estructuras = _extraer_estructuras(texto)

                for est in estructuras:
                    resultados.append({
                        "Punto": f"P-{punto:03d}",
                        "Estructura": est
                    })
                    punto += 1

                dentro_mtext = False
                buffer_texto = []
                continue

            # -------------------------------------------------
            # CONTENIDO MTEXT
            # -------------------------------------------------
            if dentro_mtext and codigo in ("1", "3"):
                if valor:
                    buffer_texto.append(valor)

    except StopIteration:
        pass

    # =====================================================
    # VALIDACIÓN FINAL (CONTRATO FUERTE)
    # =====================================================
    if not resultados:
        raise ValueError(
            "DXF válido pero no contiene estructuras detectables"
        )

    df = pd.DataFrame(resultados)

    # Garantizar columnas exactas
    df = df[["Punto", "Estructura"]]

    return df


# =========================================================
# HELPERS
# =========================================================
def _limpiar_texto(texto: str) -> str:
    """
    Limpieza fuerte de MTEXT DXF
    """

    texto = texto.replace("\\P", ",")
    texto = re.sub(r"\{[^};]*[;:]", "", texto)
    texto = texto.replace("{", "").replace("}", "")
    texto = re.sub(r"\([^)]*\)", "", texto)

    texto = texto.replace(";", ",").replace("|", ",")
    texto = re.sub(r",+", ",", texto)

    texto = texto.upper()
    texto = re.sub(r"\s+", " ", texto).strip(" ,")

    return texto


def _extraer_estructuras(texto: str) -> List[str]:
    """
    Extrae múltiples estructuras desde un texto.
    """

    posibles = re.split(r"[,\s]+", texto)

    estructuras = []

    for p in posibles:
        p = p.strip().upper()

        if _es_estructura(p):
            estructuras.append(p)

    return estructuras


def _es_estructura(texto: str) -> bool:
    """
    Patrón más estricto de estructuras:
    A-I-4, B-III-6, TS-50, CT-N, etc.
    """

    return bool(
        re.fullmatch(r"[A-Z]{1,3}-[A-Z0-9]+(?:-[A-Z0-9]+)*", texto)
    )
