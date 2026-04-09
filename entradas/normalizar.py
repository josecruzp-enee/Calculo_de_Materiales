# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import pandas as pd


# =========================================================
# LIMPIEZA BASE
# =========================================================
def limpiar_codigo(codigo: str) -> str:
    if codigo is None:
        return ""

    codigo = str(codigo).upper().strip()

    if not codigo:
        return ""

    codigo = re.sub(r"\(.*?\)", "", codigo)
    codigo = codigo.replace(",", "")
    codigo = codigo.replace(" ", "-")
    codigo = re.sub(r"[^A-Z0-9\-]", "", codigo)
    codigo = re.sub(r"-+", "-", codigo)
    codigo = codigo.strip("-")

    return codigo


# =========================================================
# PREFIJO (FIX CLAVE)
# =========================================================
def _normalizar_prefijo(codigo: str) -> str:

    if not codigo:
        return codigo

    # ya válido
    if codigo.startswith(("A-", "B-", "PC", "TS", "R", "CT", "CS", "PM", "CA", "LL")):
        return codigo

    # romanos → A-
    if re.match(r"^(I|II|III)[\-]?\d+[A-Z]?$", codigo):
        return f"A-{codigo}"

    return codigo


# =========================================================
# PARSER
# =========================================================
def _extraer_estructuras(texto: str):

    if not texto:
        return []

    texto = texto.upper()
    texto = texto.replace(",", "").replace(";", " ").replace("/", " ")

    patron = r"\b[A-Z]{1,4}(?:[-\s]?\d+)+(?:[-\s]?[A-Z0-9]+)*\b"

    return re.findall(patron, texto)


# =========================================================
# CORE
# =========================================================
def _convertir(df: pd.DataFrame):

    registros = []

    for idx, row in df.iterrows():

        texto = " ".join(str(v) for v in row.values if pd.notna(v))
        if not texto:
            continue

        texto = texto.replace("(P)", "")

        lineas = re.split(r"\n|\\P|;", texto)

        punto_actual = None

        for linea in lineas:

            linea = linea.strip()
            if not linea:
                continue

            # detectar punto
            m = re.match(r"P[-\s]?(\d+)", linea)
            if m:
                punto_actual = f"P-{m.group(1)}"
                continue

            encontrados = _extraer_estructuras(linea)

            for e in encontrados:

                est = limpiar_codigo(e)
                est = _normalizar_prefijo(est)

                if not est or not re.search(r"\d", est):
                    continue

                registros.append({
                    "Punto": punto_actual if punto_actual else f"P-{idx+1}",
                    "codigodeestructura": est,
                    "Cantidad": 1
                })

    df_out = pd.DataFrame(registros)

    if df_out.empty:
        return df_out

    df_out = (
        df_out
        .groupby(["Punto", "codigodeestructura"], as_index=False)["Cantidad"]
        .sum()
    )

    return df_out


# =========================================================
# API
# =========================================================
def normalizar_estructuras(df: pd.DataFrame):

    if not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(), ["df inválido o vacío"], []

    try:
        df_norm = _convertir(df)

        if df_norm.empty:
            return pd.DataFrame(), ["No se detectaron estructuras"], []

        return df_norm, [], []

    except Exception as e:
        return pd.DataFrame(), [str(e)], []
