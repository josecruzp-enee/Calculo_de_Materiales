# -*- coding: utf-8 -*-
"""
normalizacion_estructuras.py
Helpers: logger, normalización de datos_proyecto, tensión, limpieza de estructuras, parsing de códigos.
"""

import re
import pandas as pd


# ==========================================================
# Helpers generales
# ==========================================================
def get_logger():
    """Devuelve st.write si existe; si no, print."""
    try:
        import streamlit as st  # noqa
        return st.write
    except Exception:
        return print


def normalizar_datos_proyecto(datos_proyecto: dict) -> dict:
    """Asegura estructuras mínimas y tipos esperados."""
    datos_proyecto = datos_proyecto or {}

    cables = datos_proyecto.get("cables_proyecto", [])
    if isinstance(cables, dict) or cables is None:
        cables = []
    datos_proyecto["cables_proyecto"] = cables

    return datos_proyecto


def extraer_tension_ll_kv(x):
    """
    Devuelve la tensión L-L (kV) como float.
    Acepta:
      - 13.8
      - "13.8"
      - "7.9 LN / 13.8 LL KV"
      - "19.9 L-N / 34.5 L-L kV"
    Regla: toma el número mayor (usualmente L-L).
    """
    if x is None:
        return None
    nums = re.findall(r"\d+(?:\.\d+)?", str(x))
    if not nums:
        return None
    vals = [float(n) for n in nums]
    return max(vals) if vals else None


def encontrar_col_tension(cols, tension_ll: float):
    """
    Encuentra la columna de tensión en una hoja de materiales.
    Estrategia:
      1) Match directo por substring (ej: "13.8" dentro del header)
      2) Match numérico: extrae números del header y compara por tolerancia
    """
    if tension_ll is None:
        return None

    # 1) Match directo
    t_str = f"{float(tension_ll)}".rstrip("0").rstrip(".")
    for c in cols:
        if t_str and t_str in str(c):
            return c

    # 2) Match numérico
    for c in cols:
        nums = re.findall(r"\d+(?:\.\d+)?", str(c))
        for n in nums:
            try:
                if abs(float(n) - float(tension_ll)) < 1e-6:
                    return c
            except Exception:
                pass

    return None


# ==========================================================
# Limpieza de DF estructuras (LARGO)
# ==========================================================
def limpiar_df_estructuras(df_estructuras: pd.DataFrame, log) -> pd.DataFrame:
    """
    Espera DF LARGO con columnas mínimas:
      - Punto
      - codigodeestructura
      - cantidad (opcional; si no viene, asume 1)

    ✅ NO elimina duplicados; AGRUPA y SUMA cantidades.
    """
    filas_antes = len(df_estructuras)
    df = df_estructuras.dropna(how="all").copy()

    if "Punto" not in df.columns and "punto" in df.columns:
        df.rename(columns={"punto": "Punto"}, inplace=True)

    for col in ("Punto", "codigodeestructura"):
        if col not in df.columns:
            raise ValueError(
                f"Falta columna requerida: '{col}'. Columnas: {df.columns.tolist()}"
            )

    df["Punto"] = df["Punto"].astype(str).str.strip()
    df["codigodeestructura"] = df["codigodeestructura"].astype(str).str.strip()

    if "cantidad" not in df.columns:
        df["cantidad"] = 1
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(1).astype(int)
    df.loc[df["cantidad"] < 1, "cantidad"] = 1

    df = df[df["codigodeestructura"].notna()]
    df = df[df["codigodeestructura"].astype(str).str.strip() != ""]

    df = (
        df.groupby(["Punto", "codigodeestructura"], as_index=False)["cantidad"]
        .sum()
    )

    filas_despues = len(df)
    log(f"🧹 Filas eliminadas: {filas_antes - filas_despues}")
    return df


def _normalizar_codigo_basico(code: str) -> str:
    """
    Normalización básica de código:
      - uppercase
      - strip
      - quita sufijos tipo "(E)" "(P)" "(R)"
      - colapsa espacios (solo para códigos)
      - normaliza TS (quita espacios antes de KVA)
    """
    if code is None:
        return ""
    s = str(code).strip()
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s).strip()  # quita "(E)" etc al final
    s = re.sub(r"\s+", " ", s).strip()
    s = s.upper()

    # Normalizar transformadores tipo "TS-50 KVA" -> "TS-50KVA"
    s = re.sub(r"\bTS-?\s*(\d+(\.\d+)?)\s*KVA\b", lambda m: f"TS-{m.group(1)}KVA", s)
    s = s.replace(" TS-", "TS-").replace(" KVA", "KVA")
    return s


def explotar_codigos_por_coma(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte celdas tipo:
      "B-III-6, B-I-4B" -> 2 filas.
    Mantiene y distribuye la misma 'cantidad' a cada código separado.

    ✅ Luego agrupa y SUMA por (Punto, código).
    """
    tmp = df[["Punto", "codigodeestructura", "cantidad"]].copy()

    tmp["Punto"] = tmp["Punto"].astype(str).str.strip()
    tmp["cantidad"] = pd.to_numeric(tmp["cantidad"], errors="coerce").fillna(1).astype(int)
    tmp.loc[tmp["cantidad"] < 1, "cantidad"] = 1

    tmp["codigodeestructura"] = tmp["codigodeestructura"].astype(str).str.replace(";", ",", regex=False)
    tmp["codigodeestructura"] = tmp["codigodeestructura"].str.split(",")
    tmp = tmp.explode("codigodeestructura")

    tmp["codigodeestructura"] = tmp["codigodeestructura"].map(_normalizar_codigo_basico)
    tmp = tmp[tmp["codigodeestructura"] != ""]

    tmp = (
        tmp.groupby(["Punto", "codigodeestructura"], as_index=False)["cantidad"]
        .sum()
    )
    return tmp


def construir_estructuras_por_punto_y_conteo(df_unicas: pd.DataFrame, log):
    """
    Construye:
      - estructuras_por_punto: dict {Punto: [códigos repetidos según cantidad]}
      - conteo: dict {codigo: cantidad_total_en_proyecto}
      - tmp: DataFrame explotado con columnas (Punto, codigodeestructura, cantidad)
    """
    tmp = explotar_codigos_por_coma(df_unicas)

    conteo = (
        tmp.groupby("codigodeestructura")["cantidad"]
        .sum()
        .to_dict()
    )

    estructuras_por_punto = {}
    for punto, grp in tmp.groupby("Punto"):
        lista = []
        for _, r in grp.iterrows():
            cod = str(r["codigodeestructura"]).strip().upper()
            c = int(r["cantidad"])
            lista.extend([cod] * max(1, c))
        estructuras_por_punto[str(punto)] = lista

    log("✅ estructuras_por_punto (repitiendo por cantidad):")
    log(estructuras_por_punto)
    log("✅ conteo global (sumando cantidad):")
    log(conteo)

    return estructuras_por_punto, conteo, tmp
