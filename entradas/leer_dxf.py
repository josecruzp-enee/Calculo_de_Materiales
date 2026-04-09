# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import re
from typing import Any


def leer_dxf(archivo_dxf: Any) -> pd.DataFrame:
    """
    Lector DXF robusto para estructuras.

    ✔ Devuelve DataFrame válido
    ✔ Lanza error si no hay estructuras
    ✔ No depende estrictamente de capa
    ✔ Limpio para pipeline

    OUTPUT:
        DataFrame columnas:
            - Punto
            - Estructura
    """

    # =========================================================
    # VALIDACIÓN
    # =========================================================
    if archivo_dxf is None:
        raise ValueError("archivo_dxf es None")

    # =========================================================
    # LECTURA
    # =========================================================
    try:
        if hasattr(archivo_dxf, "seek"):
            archivo_dxf.seek(0)

        raw = archivo_dxf.read()

        if not raw:
            raise ValueError("DXF vacío o ya fue consumido")

        contenido = raw.decode("latin-1", errors="ignore")

    except Exception as e:
        raise ValueError(f"No se pudo leer el DXF: {e}")

    # =========================================================
    # TOKENIZACIÓN SEGURA (PARES)
    # =========================================================
    lineas = [l.strip() for l in contenido.splitlines() if l.strip()]

    resultados = []
    punto = 1

    it = iter(lineas)

    capa_actual = None
    dentro_mtext = False
    buffer_texto = []

    try:
        for codigo in it:
            valor = next(it)

            codigo = codigo.strip()
            valor = valor.strip()

            # -------------------------------------------------
            # CAPA
            # -------------------------------------------------
            if codigo == "8":
                capa_actual = valor.upper()

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
                if not capa_actual or "Estructuras" not in capa_actual:
                    dentro_mtext = False
                    buffer_texto = []
                    continue
                texto = ",".join(buffer_texto)

                texto = _limpiar_texto(texto)

                if texto and _es_estructura(texto):
                    resultados.append({
                        "Punto": f"P-{punto}",
                        "Estructura": texto
                    })
                    punto += 1

                dentro_mtext = False
                buffer_texto = []
                continue

            # -------------------------------------------------
            # CONTENIDO MTEXT
            # -------------------------------------------------
            if dentro_mtext and codigo in ("1", "3"):
                limpio = valor.strip()
                if limpio:
                    buffer_texto.append(limpio)

    except StopIteration:
        pass

    # =========================================================
    # VALIDACIÓN FINAL (CRÍTICA)
    # =========================================================
    if not resultados:
        raise ValueError(
            "DXF leído correctamente pero no se encontraron estructuras válidas"
        )

    return pd.DataFrame(resultados)


# =========================================================
# HELPERS
# =========================================================
def _limpiar_texto(texto: str) -> str:
    texto = texto.replace("\\P", ",")
    texto = re.sub(r"\{[^};]*[;:]", "", texto)
    texto = texto.replace("{", "").replace("}", "")
    texto = re.sub(r"\([^)]*\)", "", texto)
    texto = texto.replace(";", ",").replace("|", ",")
    texto = re.sub(r",+", ",", texto)
    texto = re.sub(r"\s+", " ", texto).strip(" ,")
    return texto


def _es_estructura(texto: str) -> bool:
    """
    Detecta estructuras tipo:
    A-III-1, B-I-4, TS-50, etc.
    """
    return bool(re.search(r"[A-Z]+-[A-Z0-9\-]+", texto))
