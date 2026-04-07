# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import re

from ayuda.debug import debug_guardar


def leer_dxf(archivo_dxf) -> pd.DataFrame:
    """
    Lee un archivo DXF (MTEXT) y extrae estructuras.

    INPUT:
        archivo_dxf: UploadedFile | file-like

    OUTPUT:
        DataFrame columnas:
            - Punto
            - Estructura
    """

    if archivo_dxf is None:
        raise ValueError("archivo_dxf es None")

    # =========================================================
    # 🔥 LECTURA SEGURA (FIX CRÍTICO)
    # =========================================================
    try:
        if hasattr(archivo_dxf, "seek"):
            archivo_dxf.seek(0)  # 🔥 resetear puntero SIEMPRE

        raw = archivo_dxf.read()

        if not raw:
            raise ValueError("DXF vacío o ya fue consumido")

        contenido = raw.decode("latin-1", errors="ignore")

    except Exception as e:
        raise ValueError(f"No se pudo leer el DXF: {e}")

    # =========================================================
    # PROCESAMIENTO BASE
    # =========================================================
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

                if codigo == "8":
                    capa = valor.upper()

                if codigo == "1":
                    texto += " " + valor

                i += 2

            # =================================================
            # FILTRO DE CAPA
            # =================================================
            if capa != "ESTRUCTURAS":
                continue

            if not texto.strip():
                continue

            # =================================================
            # LIMPIEZA
            # =================================================

            # saltos AutoCAD
            texto = texto.replace("\\P", ",")

            # eliminar formato tipo {C7:
            texto = re.sub(r"\{[^};]*[;:]", "", texto)

            # eliminar llaves
            texto = texto.replace("{", "").replace("}", "")

            # eliminar etiquetas tipo P-57
            texto = re.sub(r"\bP-\d+\b", "", texto)

            # eliminar (P), (E), etc
            texto = re.sub(r"\([^)]*\)", "", texto)

            # normalizar separadores
            texto = texto.replace(";", ",")
            texto = texto.replace("|", ",")

            # normalizar comas múltiples
            texto = re.sub(r",+", ",", texto)

            # separar códigos pegados por espacio
            texto = re.sub(r"\s(?=[A-Z]+-)", ",", texto)

            # limpiar espacios
            texto = re.sub(r"\s+", " ", texto).strip(" ,")

            # =================================================
            # OUTPUT
            # =================================================
            resultados.append({
                "Punto": f"P-{punto}",
                "Estructura": texto
            })

            punto += 1

        else:
            i += 1

    # =========================================================
    # OUTPUT FINAL
    # =========================================================
    if not resultados:
        df = pd.DataFrame(columns=["Punto", "Estructura"])
    else:
        df = pd.DataFrame(resultados)

    # =========================================================
    # DEBUG
    # =========================================================
    print("\n=== DEBUG DXF ===")
    print("registros encontrados:", len(df))

    debug_guardar("DXF - salida", df)
    debug_guardar("DXF - texto limpio", resultados[:5])

    return df
