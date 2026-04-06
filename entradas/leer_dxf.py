# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import re


# =========================================================
# REGEX ESTRUCTURAS
# =========================================================
RE_TOKEN = re.compile(
    r"""
    (?:PC|PM|PT)-[A-Z0-9\.\-]+
    |CA-[A-Z0-9\-]+
    |A-[A-Z0-9\-]+
    |B-[A-Z0-9\-]+
    |CT-[A-Z0-9\-]+
    |CS-[A-Z0-9\-]+
    |TS-[A-Z0-9\.\-]+
    |TD[A-Z0-9\-]*|TF[A-Z0-9\-]*|TR[A-Z0-9\-]*|TX[A-Z0-9\-]*
    |LL-[A-Z0-9\-]+|LS-[A-Z0-9\-]+
    |R-\d+[A-Z0-9\-]*
    """,
    re.VERBOSE,
)


# =========================================================
# LECTOR DXF POR MTEXT + CAPA
# =========================================================
def leer_dxf(archivo_dxf) -> pd.DataFrame:

    if archivo_dxf is None:
        raise ValueError("archivo_dxf es None")

    try:
        contenido = archivo_dxf.read().decode("latin-1", errors="ignore")
    except Exception:
        raise ValueError("No se pudo leer el DXF")

    lineas = [l.strip() for l in contenido.splitlines()]

    resultados = []
    punto = 1

    i = 0
    while i < len(lineas) - 1:

        # =========================
        # DETECTAR ENTIDAD MTEXT
        # =========================
        if lineas[i] == "0" and lineas[i + 1] == "MTEXT":

            i += 2
            capa = None
            texto = ""

            # =========================
            # LEER BLOQUE MTEXT
            # =========================
            while i < len(lineas) - 1 and lineas[i] != "0":

                codigo = lineas[i]
                valor = lineas[i + 1]

                # capa
                if codigo == "8":
                    capa = valor.upper()

                # contenido texto
                if codigo == "1":
                    texto += " " + valor

                i += 2

            # =========================
            # FILTRAR SOLO CAPA ESTRUCTURAS
            # =========================
            if capa != "ESTRUCTURAS":
                continue

            if not texto.strip():
                continue

            # limpiar formato MTEXT
            texto = texto.replace("\\P", " ")
            texto = re.sub(r"\s+", " ", texto).strip().upper()

            # =========================
            # EXTRAER TOKENS
            # =========================
            tokens = RE_TOKEN.findall(texto)

            if tokens:
                for t in tokens:
                    resultados.append({
                        "Punto": f"P-{punto}",
                        "Estructura": t
                    })

                punto += 1

        else:
            i += 1

    if not resultados:
        return pd.DataFrame()

    return pd.DataFrame(resultados)
