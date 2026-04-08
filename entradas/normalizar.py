# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import pandas as pd
from ayuda.debug import debug_guardar


# ==========================================================
# HELPERS INTERNOS (única fuente de verdad)
# ==========================================================
def limpiar_codigo(codigo: str) -> str:
    if codigo is None:
        return ""
    codigo = str(codigo).strip().upper()
    if not codigo:
        return ""
    codigo = re.sub(r"\(.*?\)", "", codigo)
    codigo = codigo.replace(" ", "")
    codigo = re.sub(r"[^A-Z0-9\-\.\+]", "", codigo)
    return codigo


def _expandir_multiplicador(token: str):
    if not token:
        return []

    token = token.strip().upper()

    match = re.match(r"^\s*(\d+)\s*[xX]\s*(.+)$", token)
    if match:
        n = int(match.group(1))
        val = match.group(2).strip()
        return [val] * n

    match = re.match(r"^\s*(\d+)[xX]([A-Z0-9\-\.]+)$", token)
    if match:
        n = int(match.group(1))
        val = match.group(2).strip()
        return [val] * n

    return [token]


def _split_bloques(texto: str):
    if texto is None:
        return []

    texto = texto.replace(";", ",")
    texto = texto.replace("|", ",")

    partes = re.split(r"[,\n]+", texto)

    resultado = []
    buffer = None

    for p in partes:
        p = p.strip()
        if not p:
            continue

        # une "3 X" con siguiente
        if re.match(r"^\d+\s*[xX]$", p):
            buffer = p
            continue

        if buffer:
            p = f"{buffer} {p}"
            buffer = None

        resultado.append(p)

    return resultado


def expandir_lista_codigos(texto: str):

    debug_guardar("raw_texto_entrada", texto)

    if texto is None:
        return []

    texto = str(texto).upper()

    # limpieza DXF
    texto = re.sub(r"\{[^:]*:", "", texto)
    texto = texto.replace("{", "").replace("}", "")
    texto = texto.replace("\\P", ",")

    partes = _split_bloques(texto)
    resultado = []

    for p in partes:
        if not p:
            continue

        p = re.sub(r"\(.*?\)", "", p)

        tokens = _expandir_multiplicador(p)

        for t in tokens:
            t = t.strip()
            if not t:
                continue

            codigo = limpiar_codigo(t)
            if codigo:
                resultado.append(codigo)

    debug_guardar("codigos_expandidos", resultado)
    return resultado


# ==========================================================
# DETECCIÓN DE POSTE (mínima)
# ==========================================================
def _es_poste(codigo: str) -> bool:
    if not codigo:
        return False
    codigo = codigo.upper()
    return codigo.startswith(("PC-", "PM-", "PT-"))


# ==========================================================
# CONVERSIÓN A FORMATO LARGO (CORE)
# ==========================================================
def _convertir_a_largo(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()
    df.columns = df.columns.str.strip()

    registros = []

    for idx, row in df.iterrows():

        punto = row.get("Punto") or row.get("punto") or f"P-{idx+1}"

        estructura_raw = None
        for col in df.columns:
            if col.lower() in ["estructura", "estructuras", "codigodeestructura"]:
                estructura_raw = row.get(col)
                break

        if estructura_raw is None:
            continue

        lista_codigos = expandir_lista_codigos(estructura_raw)

        poste_detectado = None

        for raw in lista_codigos:

            if not raw:
                continue

            if _es_poste(raw):
                poste_detectado = limpiar_codigo(raw)
                continue

            cod = limpiar_codigo(raw)

            if not cod:
                continue

            if re.match(r"^\d+X$", cod):
                continue

            if cod == "LL-1":
                continue

            registros.append({
                "punto": str(punto).strip(),
                "poste": poste_detectado,
                "codigodeestructura": cod,
                "cantidad": 1
            })

    return pd.DataFrame(registros)


# ==========================================================
# FUNCIÓN PÚBLICA
# ==========================================================
def normalizar_estructuras(df: pd.DataFrame) -> pd.DataFrame:
    return _convertir_a_largo(df)
