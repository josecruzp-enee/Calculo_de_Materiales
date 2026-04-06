# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import re


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

        if lineas[i] == "0" and lineas[i + 1] == "MTEXT":

            i += 2
            capa = None
            texto = ""

            while i < len(lineas) - 1 and lineas[i] != "0":

                codigo = lineas[i]
                valor = lineas[i + 1]

                # capa
                if codigo == "8":
                    capa = valor.upper()

                # contenido
                if codigo == "1":
                    texto += " " + valor

                i += 2

            # =========================
            # FILTRO DE CAPA
            # =========================
            if capa != "ESTRUCTURAS":
                continue

            if not texto.strip():
                continue

            # =========================
            # 🔥 LIMPIEZA MTEXT (CLAVE)
            # =========================

            # 1. convertir saltos de línea de AutoCAD
            texto = texto.replace("\\P", ",")

            # 2. eliminar formato tipo {C7:
            texto = re.sub(r"\{.*?:", "", texto)

            # 3. eliminar llaves
            texto = texto.replace("}", "")

            # 4. normalizar espacios
            texto = re.sub(r"\s+", " ", texto).strip()

            # =========================
            # OUTPUT CRUDO CONTROLADO
            # =========================
            resultados.append({
                "Punto": f"P-{punto}",
                "Estructura": texto
            })

            punto += 1

        else:
            i += 1

    if not resultados:
        return pd.DataFrame()

    return pd.DataFrame(resultados)
