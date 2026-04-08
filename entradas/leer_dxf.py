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
    # 🔥 LECTURA SEGURA
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

            # 🔥 NUEVO: acumulador correcto de líneas MTEXT
            lineas_mtext = []

            # =================================================
            # LECTURA MTEXT (MULTILÍNEA REAL)
            # =================================================
            while i < len(lineas) - 1 and lineas[i] != "0":

                codigo = lineas[i]
                valor = lineas[i + 1]

                if codigo == "8":
                    capa = valor.upper()

                # 🔥 FIX CRÍTICO
                if codigo in ("1", "3"):
                    limpio = valor.strip()
                    if limpio:
                        lineas_mtext.append(limpio)

                i += 2

            # 🔥 reconstrucción final del texto
            texto = ",".join(lineas_mtext)

            # =================================================
            # FILTRO DE CAPA (ROBUSTO)
            # =================================================
            if not capa or "ESTRUCT" not in capa:
                continue

            if not texto.strip():
                continue

            # =================================================
            # LIMPIEZA
            # =================================================

            texto = texto.replace("\\P", ",")

            texto = re.sub(r"\{[^};]*[;:]", "", texto)

            texto = texto.replace("{", "").replace("}", "")

            # eliminar (P), (E), etc
            texto = re.sub(r"\([^)]*\)", "", texto)

            texto = texto.replace(";", ",")
            texto = texto.replace("|", ",")

            texto = re.sub(r",+", ",", texto)

            # ⚠️ NO romper TS-37.5 KVA
            # texto = re.sub(r"\s+(?=[A-Z]{1,3}-\d)", ",", texto)

            texto = re.sub(r"\s+", " ", texto).strip(" ,")

            if not texto:
                continue

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

    debug_guardar("DXF_DF_FINAL", df)

    debug_guardar("DXF_TODAS", resultados)

    debug_guardar(
        "DXF_UNICAS",
        sorted({r["Estructura"] for r in resultados})
    )

    debug_guardar(
        "DXF_SOLO_CS",
        sorted({r["Estructura"] for r in resultados if "CS" in str(r["Estructura"])})
    )

    return df
