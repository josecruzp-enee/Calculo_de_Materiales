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

    # limpieza mínima (no destructiva)
    texto = texto.replace(";", " ").replace("/", " ")
    texto = texto.replace("\\P", " ")

    # 🔥 PATRONES CONTROLADOS (NO GENÉRICOS)
    PATRONES = [
        r"A-[IVX]+-\d+[A-Z]?",
        r"B-[IVX]+-\d+[A-Z]?",
        r"DTN?-[IVX]+-\d+",
        r"ER-[IVX]+-\d+[A-Z]?",
        r"H-[IVX]+-\d+",
        r"TH-[IVX]+-\d+",
        r"TM-[IVX]+-\d+[A-Z]?",
        r"G[B]?-[IVX]+-\d+[A-Z]?",

        r"R-\d+[A-Z]?",
        r"RH-\d+",
        r"RTH-\d+",

        r"TS-\d+(?:\.\d+)?\s?KVA",
        r"TD-\d+(?:\.\d+)?\s?KVA",
        r"TT-\d+(?:\.\d+)?\s?KVA",

        r"CS-\d+",
        r"CA-\d+",
        r"CT-[A-Z]",

        r"LL-\d+(?:-\d+[A-Z]+)+",

        r"PC[A-Z]?-\d+",
        r"PM-\d+",
        r"PT-\d+",
    ]

    patron_global = re.compile("|".join(PATRONES))

    encontrados = patron_global.findall(texto)

    return [e.strip() for e in encontrados]

# =========================================================
# CORE
# =========================================================
def _convertir(df: pd.DataFrame):

    registros = []

    VALIDOS_BASE = (
        "A-", "B-", "PC", "TS", "R", "CT", "CS", "PM", "CA", "LL",
        "PT", "TT", "TD", "DT", "DTN", "ER", "H", "TH", "TM",
        "GB", "G", "AC", "EM", "SC", "SP", "RH", "RTH", "PCA"
    )

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

            m = re.match(r"P[-\s]?(\d+)", linea)
            if m:
                punto_actual = f"P-{m.group(1)}"
                continue

            encontrados = _extraer_estructuras(linea)

            for e in encontrados:

                est = limpiar_codigo(e)
                est = _normalizar_prefijo(est)

                # ✔ SOLO estructuras válidas reales
                if not est.startswith(VALIDOS_BASE):
                    continue

                if not re.search(r"\d", est):
                    continue

                registros.append({
                    "Punto": punto_actual if punto_actual else f"P-{idx+1}",
                    "codigodeestructura": est,
                    "Cantidad": 1
                })

    df_out = pd.DataFrame(registros)

    if df_out.empty:
        return df_out

    return (
        df_out
        .groupby(["Punto", "codigodeestructura"], as_index=False)["Cantidad"]
        .sum()
    )
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
