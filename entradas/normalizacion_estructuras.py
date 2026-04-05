# -*- coding: utf-8 -*-
"""
normalizacion_estructuras.py

Motor completo de normalización de estructuras ENEE.
"""

import re
import pandas as pd


# =========================================================
# LOGGER
# =========================================================

def get_logger():
    try:
        import streamlit as st
        return st.write
    except Exception:
        return print


# =========================================================
# NORMALIZAR CÓDIGOS
# =========================================================

def _normalizar_codigo(code: str) -> str:

    if code is None:
        return ""

    s = str(code).upper().strip()

    # quitar paréntesis (P), (E), etc
    s = re.sub(r"\([^)]*\)", "", s)

    # limpiar espacios
    s = re.sub(r"\s+", " ", s)

    # normalizar TS (transformadores)
    s = re.sub(
        r"\bTS-?\s*(\d+(\.\d+)?)\s*KVA\b",
        lambda m: f"TS-{m.group(1)}KVA",
        s
    )

    return s.strip()


# =========================================================
# LIMPIEZA BASE
# =========================================================

def limpiar_df_estructuras(df: pd.DataFrame, log) -> pd.DataFrame:

    df = df.dropna(how="all").copy()

    if "Punto" not in df.columns and "punto" in df.columns:
        df.rename(columns={"punto": "Punto"}, inplace=True)

    if "cantidad" not in df.columns:
        df["cantidad"] = 1

    df["Punto"] = df["Punto"].astype(str).str.strip()
    df["codigodeestructura"] = df["codigodeestructura"].astype(str).str.strip()

    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(1).astype(int)
    df.loc[df["cantidad"] < 1, "cantidad"] = 1

    df = df[df["codigodeestructura"] != ""]

    return df


# =========================================================
# SPLIT INTELIGENTE
# =========================================================

def _split_codigos(texto):

    limpio = re.sub(r"\(.*?\)", "", str(texto)).upper()

    # proteger TS
    limpio = re.sub(
        r"(TS-?\s*\d+(\.\d+)?\s*KVA)",
        lambda m: m.group(0).replace(" ", "_"),
        limpio
    )

    partes = re.split(r"[,\s]+", limpio)

    resultado = []

    i = 0
    while i < len(partes):

        item = partes[i].replace("_", " ").strip()

        if not item:
            i += 1
            continue

        # multiplicador: 3 x CS-2
        if item.isdigit() and i + 2 < len(partes):
            if partes[i + 1].lower() == "x":
                codigo = partes[i + 2].replace("_", " ").strip()
                cantidad = int(item)

                resultado.extend([codigo] * cantidad)
                i += 3
                continue

        if item in ["X", "KVA"]:
            i += 1
            continue

        resultado.append(item)
        i += 1

    return resultado


# =========================================================
# EXPLOTAR
# =========================================================

def explotar_estructuras(df):

    filas = []

    for _, row in df.iterrows():

        punto = row["Punto"]
        cantidad_base = int(row.get("cantidad", 1))

        codigos = _split_codigos(row["codigodeestructura"])

        for cod in codigos:

            cod = _normalizar_codigo(cod)

            if not cod:
                continue

            filas.append({
                "Punto": punto,
                "codigodeestructura": cod,
                "cantidad": cantidad_base
            })

    df_out = pd.DataFrame(filas)

    df_out = (
        df_out.groupby(["Punto", "codigodeestructura"], as_index=False)["cantidad"]
        .sum()
    )

    return df_out


# =========================================================
# FUNCIÓN FINAL
# =========================================================

def construir_estructuras_por_punto_y_conteo(df, log):

    df = explotar_estructuras(df)

    conteo = (
        df.groupby("codigodeestructura")["cantidad"]
        .sum()
        .to_dict()
    )

    estructuras_por_punto = {}

    for punto, grp in df.groupby("Punto"):

        lista = []

        for _, r in grp.iterrows():
            lista.extend([r["codigodeestructura"]] * int(r["cantidad"]))

        estructuras_por_punto[punto] = lista

    log("✔ estructuras_por_punto:")
    log(estructuras_por_punto)

    log("✔ conteo:")
    log(conteo)

    return estructuras_por_punto, conteo, df
