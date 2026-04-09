# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import pandas as pd


# =========================================================
# LIMPIEZA
# =========================================================
def limpiar_codigo(codigo: str) -> str:
    if not codigo:
        return ""

    codigo = str(codigo).upper().strip()

    codigo = re.sub(r"\(.*?\)", "", codigo)
    codigo = codigo.replace(",", "")
    codigo = codigo.replace(" ", "-")

    codigo = re.sub(r"[^A-Z0-9\.\-]", "", codigo)
    codigo = re.sub(r"-+", "-", codigo)

    return codigo.strip("-")


# =========================================================
# PATRÓN
# =========================================================
PATRON = re.compile(
    r"""
    (A-[IVX]+-\d+[A-Z]?)|
    (B-[IVX]+-\d+[A-Z]?)|
    (DTN?-[IVX]+-\d+)|
    (ER-[IVX]+-\d+[A-Z]?)|
    (H-[IVX]+-\d+)|
    (TH-[IVX]+-\d+)|
    (TM-[IVX]+-\d+[A-Z]?)|
    (G[B]?-[IVX]+-\d+[A-Z]?)|

    (R-\d+[A-Z]?)|
    (RH-\d+)|
    (RTH-\d+)|

    (TS-\d+(?:\.\d+)?\s?KVA)|
    (TD-\d+(?:\.\d+)?\s?KVA)|
    (TT-\d+(?:\.\d+)?\s?KVA)|

    (CS-[12])|
    (CA-\d+)|
    (CT-[A-Z])|

    (LL-\d+(?:-\d+[A-Z]+)+)|

    (PC[A-Z]?-\d+)|
    (PM-\d+)|
    (PT-\d+)
    """,
    re.VERBOSE
)


# =========================================================
# EXTRAER
# =========================================================
def _extraer_estructuras(texto: str):

    if not texto:
        return []

    texto = str(texto).upper()

    texto = texto.replace("\\P", " ")
    texto = texto.replace(";", " ")
    texto = texto.replace("/", " ")

    encontrados = PATRON.findall(texto)

    return [item for grupo in encontrados for item in grupo if item]


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

            estructuras = _extraer_estructuras(linea)

            for e in estructuras:

                est = limpiar_codigo(e)

                if not est or not re.search(r"\d", est):
                    continue

                registros.append({
                    "Punto": punto_actual or f"P-{idx+1}",

                    # 🔥 ESTE ES EL CONTRATO REAL
                    "codigodeestructura": est,

                    # opcional (futuro)
                    "Estructura": est,

                    "Cantidad": 1
                })

    df_out = pd.DataFrame(registros)

    if df_out.empty:
        return df_out

    return (
        df_out
        .groupby(
            ["Punto", "codigodeestructura", "Estructura"],
            as_index=False
        )["Cantidad"]
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
