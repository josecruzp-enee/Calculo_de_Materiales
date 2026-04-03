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
    if code is None:
        return ""

    s = str(code)

    # 🔥 limpiar cualquier (P), (E), etc
    s = re.sub(r"\([^)]*\)", "", s)

    s = re.sub(r"\s+", " ", s).strip().upper()

    # 🔥 normalizar TS con decimales
    s = re.sub(
        r"\bTS-?\s*(\d+(\.\d+)?)\s*KVA\b",
        lambda m: f"TS-{m.group(1)}KVA",
        s
    )

    return s


def explotar_codigos_por_coma(df: pd.DataFrame) -> pd.DataFrame:

    tmp = df[["Punto", "codigodeestructura", "cantidad"]].copy()

    tmp["Punto"] = tmp["Punto"].astype(str).str.strip()
    tmp["cantidad"] = pd.to_numeric(tmp["cantidad"], errors="coerce").fillna(1).astype(int)
    tmp.loc[tmp["cantidad"] < 1, "cantidad"] = 1

    def _split_codigos(x):
        if isinstance(x, list):
            base = [
                re.sub(r"\(.*?\)", "", str(i)).strip().upper()
                for i in x if str(i).strip()
            ]
        else:
            limpio = re.sub(r"\(.*?\)", "", str(x)).upper()

            # 🔥 PROTEGER TRANSFORMADORES (TS-37.5 KVA)
            limpio = re.sub(
                r"(TS-?\s*\d+(\.\d+)?\s*KVA)",
                lambda m: m.group(1).replace(" ", "_"),
                limpio
            )

            base = re.split(r"[,\s]+", limpio)

        resultado = []

        i = 0
        while i < len(base):
            item = base[i].replace("_", " ").strip()

            if not item:
                i += 1
                continue

            # 🔥 MULTIPLICADOR: 3 x CS-2
            if item.isdigit() and i + 2 < len(base):
                if base[i + 1] in ["X", "x"]:
                    codigo = base[i + 2].replace("_", " ").strip()
                    cantidad = int(item)

                    resultado.extend([codigo] * cantidad)
                    i += 3
                    continue

            # 🔥 eliminar basura
            if item in ["X", "KVA"]:
                i += 1
                continue

            resultado.append(item)
            i += 1

        return resultado

    # 🔥 aplicar split inteligente
    tmp["codigodeestructura"] = tmp["codigodeestructura"].apply(_split_codigos)

    # 🔥 explotar lista
    tmp = tmp.explode("codigodeestructura")

    # 🔥 normalizar final (usa tu función existente)
    tmp["codigodeestructura"] = tmp["codigodeestructura"].map(_normalizar_codigo_basico)

    # 🔥 eliminar vacíos
    tmp = tmp[tmp["codigodeestructura"] != ""]

    # 🔥 agrupar cantidades
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
