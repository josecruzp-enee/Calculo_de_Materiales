# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import pandas as pd


# ==========================================================
# API (usado por otros módulos)
# ==========================================================
def limpiar_codigo(codigo: str) -> str:
    if codigo is None:
        return ""

    codigo = str(codigo).strip().upper()
    if not codigo:
        return ""

    codigo = re.sub(r"\(.*?\)", "", codigo)     # quitar paréntesis
    codigo = codigo.replace(" ", "")
    codigo = re.sub(r"[^A-Z0-9\-\.\+]", "", codigo)

    return codigo


# ==========================================================
# INTERNOS
# ==========================================================
def _norm_col(s: str) -> str:
    return (
        str(s).strip().lower()
        .replace(" ", "")
        .replace("á","a").replace("é","e")
        .replace("í","i").replace("ó","o").replace("ú","u")
    )


def _split_bloques(texto: str):
    if texto is None:
        return []

    texto = str(texto)
    texto = texto.replace("\\P", "\n")
    texto = texto.replace(",", "\n")
    texto = texto.replace(";", "\n")
    texto = texto.replace("|", "\n")

    texto = re.sub(r"\n+", "\n", texto)

    return [p.strip() for p in texto.split("\n") if p.strip()]


def _expandir(token: str):
    m = re.match(r"^\s*(\d+)\s*[xX]\s*(.+)$", token)
    if m:
        return [m.group(2)] * int(m.group(1))
    return [token]


def _resolver_catalogo(codigo: str) -> str:
    # Ejemplo: luminarias LL-
    if codigo.startswith("LL-"):
        if re.search(r"LL-\d+-\d+W", codigo):
            return codigo
        return f"{codigo}-50W"
    return codigo


# ==========================================================
# CORE
# ==========================================================
def _convertir_a_largo(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    registros = []

    for idx, row in df.iterrows():

        # -------------------------
        # PUNTO
        # -------------------------
        punto = row.get("Punto") or row.get("punto") or f"P-{idx+1}"
        punto = str(punto).strip()

        # -------------------------
        # DETECTAR COLUMNA DE ESTRUCTURAS
        # -------------------------
        estructura_raw = None

        for col in df.columns:
            col_norm = _norm_col(col)

            if col_norm in {"estructura", "estructuras", "codigodeestructura"}:
                estructura_raw = row.get(col)
                break

        if estructura_raw is None:
            continue

        # -------------------------
        # EXPANDIR
        # -------------------------
        partes = _split_bloques(estructura_raw)

        codigos = []
        for p in partes:
            for t in _expandir(p):
                c = limpiar_codigo(t)
                if c:
                    codigos.append(c)

        # -------------------------
        # CLASIFICAR
        # -------------------------
        poste = None
        estructuras = []

        for c in codigos:

            # Detecta P, PC, etc.
            if re.match(r"^P[C]?-?\d+[A-Z]?$", c):
                num = re.findall(r"\d+", c)[0]
                poste = f"P-{num}"
            else:
                estructuras.append(c)

        punto_final = poste if poste else punto

        # -------------------------
        # OUTPUT
        # -------------------------
        for est in estructuras:
            est_final = _resolver_catalogo(est)

            registros.append({
                "Punto": punto_final,
                "codigodeestructura": est_final,
                "cantidad": 1
            })

    return pd.DataFrame(registros)


# ==========================================================
# FUNCIÓN PÚBLICA
# ==========================================================
def normalizar_estructuras(df: pd.DataFrame):

    if not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(), ["df inválido o vacío"], []

    try:
        df_norm = _convertir_a_largo(df)

        if df_norm.empty:
            return pd.DataFrame(), ["No se detectaron estructuras válidas"], []

        return df_norm, [], []

    except Exception as e:
        return pd.DataFrame(), [str(e)], []
