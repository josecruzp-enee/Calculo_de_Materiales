# -*- coding: utf-8 -*-
"""
normalizacion_estructuras.py

Motor de normalización de estructuras ENEE.
Versión robusta (sin errores de tipo / None / columnas faltantes)
"""

import re
import pandas as pd


# =========================================================
# NORMALIZAR CÓDIGOS
# =========================================================
def _normalizar_codigo(code: str) -> str:

    if code is None:
        return ""

    s = str(code).upper().strip()

    # quitar paréntesis
    s = re.sub(r"\([^)]*\)", "", s)

    # limpiar espacios
    s = re.sub(r"\s+", " ", s).strip()

    # espacios alrededor de guiones
    s = re.sub(r"\s*-\s*", "-", s)

    # =========================
    # NORMALIZACIONES CLAVE
    # =========================

    # TS 50 KVA → TS-50KVA
    s = re.sub(
        r"\bTS-?\s*(\d+(\.\d+)?)\s*KVA\b",
        lambda m: f"TS-{m.group(1)}KVA",
        s
    )

    # CT N → CT-N
    s = re.sub(r"\bCT\s+N\b", "CT-N", s)

    # R 2 → R-2
    s = re.sub(r"\bR\s+(\d+)\b", r"R-\1", s)

    # PC 45 → PC-45
    s = re.sub(r"\b(PC|PM|PT)\s+(\d+)\b", r"\1-\2", s)

    # TS-50 → TS-50KVA
    if re.match(r"^TS-\d+(\.\d+)?$", s):
        s = s + "KVA"

    # patrón válido
    if re.match(r"^[A-Z]{1,3}-[A-Z0-9\-\.]+$", s):
        return s

    return s.strip()


# =========================================================
# VALIDADOR SIMPLE DE FORMATO
# =========================================================
def _es_codigo_valido(cod: str) -> bool:
    if cod is None:
        return False
    return bool(re.match(r"^[A-Z]{1,3}-[A-Z0-9\-\.]+$", str(cod).strip()))


# =========================================================
# LIMPIEZA BASE
# =========================================================
def limpiar_df_estructuras(df: pd.DataFrame) -> pd.DataFrame:

    if df is None or df.empty:
        return pd.DataFrame(columns=["Punto", "codigodeestructura", "cantidad"])

    df = df.dropna(how="all").copy()

    # normalizar nombres de columnas
    df.columns = [str(c).strip() for c in df.columns]

    if "Punto" not in df.columns and "punto" in df.columns:
        df.rename(columns={"punto": "Punto"}, inplace=True)

    if "codigodeestructura" not in df.columns:
        raise ValueError("Falta columna 'codigodeestructura'")

    if "cantidad" not in df.columns:
        df["cantidad"] = 1

    df["Punto"] = df["Punto"].astype(str).str.strip()
    df["codigodeestructura"] = df["codigodeestructura"].astype(str).str.strip()

    df["cantidad"] = (
        pd.to_numeric(df["cantidad"], errors="coerce")
        .fillna(1)
        .astype(int)
    )

    df.loc[df["cantidad"] < 1, "cantidad"] = 1

    df = df[df["codigodeestructura"] != ""]

    return df


# =========================================================
# SPLIT SEGURO
# =========================================================
def _split_codigos(texto):

    if texto is None:
        return []

    texto = str(texto).upper()

    # quitar paréntesis
    texto = re.sub(r"\(.*?\)", "", texto)

    bloques = re.split(r",", texto)

    resultado = []

    for bloque in bloques:

        partes = bloque.strip().split()

        i = 0
        while i < len(partes):

            item = partes[i]

            # multiplicador: 3 x CS-2
            if item.isdigit() and i + 2 < len(partes):
                if partes[i + 1].lower() == "x":
                    codigo = partes[i + 2]
                    cantidad = int(item)
                    resultado.extend([codigo] * cantidad)
                    i += 3
                    continue

            resultado.append(item)
            i += 1

    return resultado


# =========================================================
# EXPLOTAR A FORMATO LARGO
# =========================================================
def explotar_estructuras(df):

    if df is None or df.empty:
        return pd.DataFrame(columns=["Punto", "codigodeestructura", "cantidad"])

    if "Punto" not in df.columns or "codigodeestructura" not in df.columns:
        raise ValueError("Columnas requeridas no encontradas")

    filas = []

    for _, row in df.iterrows():

        punto = str(row.get("Punto", "")).strip()
        cantidad_base = int(row.get("cantidad", 1) or 1)

        codigos = _split_codigos(row.get("codigodeestructura"))

        for cod in codigos:

            cod = _normalizar_codigo(cod)

            if not cod or not _es_codigo_valido(cod):
                continue

            filas.append({
                "Punto": punto,
                "codigodeestructura": cod,
                "cantidad": cantidad_base
            })

    df_out = pd.DataFrame(
        filas,
        columns=["Punto", "codigodeestructura", "cantidad"]
    )

    if df_out.empty:
        return df_out

    df_out = (
        df_out.groupby(["Punto", "codigodeestructura"], as_index=False)["cantidad"]
        .sum()
    )

    return df_out


# =========================================================
# FUNCIÓN FINAL DEL MOTOR
# =========================================================
def construir_estructuras_por_punto_y_conteo(df):

    df = limpiar_df_estructuras(df)
    df = explotar_estructuras(df)

    if df.empty:
        return {}, {}, df

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

    return estructuras_por_punto, conteo, df
