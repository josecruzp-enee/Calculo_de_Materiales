# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import pandas as pd


# =========================================================
# LIMPIEZA DXF (CRÍTICO)
# =========================================================
def limpiar_texto_dxf(texto: str) -> str:

    if not texto:
        return ""

    texto = str(texto)

    # 🔥 eliminar formato DXF
    texto = re.sub(r"\{.*?;", "", texto)

    texto = texto.replace("{", "")
    texto = texto.replace("}", "")
    texto = texto.replace("\\P", " ")

    return texto


# =========================================================
# LIMPIEZA CÓDIGO
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

    codigo = codigo.replace("-KVA", "KVA")

    return codigo.strip("-")


# =========================================================
# PATRÓN
# =========================================================
PATRON = re.compile(
    r"""
    (A-[IVX]+-\d+[A-Z]?)|
    (B-[IVX]+-\d+[A-Z]?)|
    (PC[A-Z]?-\d+)|
    (TS-\d+(?:\.\d+)?KVA)|
    (CT-[A-Z])|
    (R-\d+[A-Z]?)|
    (LL-\d+(?:-\d+[A-Z]+)+)
    """,
    re.VERBOSE
)


# =========================================================
# CORE
# =========================================================
def _convertir(df: pd.DataFrame):

    registros = []

    for idx, row in df.iterrows():

        texto = " ".join(str(v) for v in row.values if pd.notna(v))
        texto = limpiar_texto_dxf(texto)

        if not texto:
            continue

        texto_upper = texto.upper()

        # =====================================================
        # DETECTAR PUNTO
        # =====================================================
        m = re.search(r"P[-\s]?(\d+)", texto_upper)
        punto = f"P-{m.group(1)}" if m else f"P-{idx+1}"

        # =====================================================
        # 🔥 TOKENIZAR (CLAVE - IDEA DEL CÓDIGO VIEJO)
        # =====================================================
        tokens = re.findall(r'\S+(?:\s*\([EPDR]\))?', texto_upper)

        for token in tokens:

            # =====================================================
            # DETECTAR TIPO (P, D, E, R)
            # =====================================================
            m_tipo = re.search(r'\((P|D|E|R)\)', token)

            if not m_tipo:
                continue

            tipo = m_tipo.group(1)

            # 🔥 SOLO PROYECTADO
            if tipo != "P":
                continue

            # =====================================================
            # LIMPIAR TOKEN → QUITAR (P)
            # =====================================================
            est_raw = re.sub(r'\s*\([EPDR]\)', '', token)

            est = limpiar_codigo(est_raw)

            if not est:
                continue

            # =====================================================
            # FILTRO FINAL: SOLO ESTRUCTURAS VÁLIDAS
            # =====================================================
            if not PATRON.match(est):
                continue

            registros.append({
                "Punto": punto,
                "codigodeestructura": est,
                "Estructura": est,
                "Cantidad": 1
            })

    df_out = pd.DataFrame(registros)

    if df_out.empty:
        return pd.DataFrame(columns=[
            "Punto",
            "codigodeestructura",
            "Estructura",
            "Cantidad"
        ])

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
            return df_norm, ["No se detectaron estructuras"], []

        return df_norm, [], []

    except Exception as e:
        return pd.DataFrame(), [str(e)], []
