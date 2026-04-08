# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import pandas as pd
from ayuda.debug import debug_guardar


# ==========================================================
# DEBUG HELPERS
# ==========================================================
def _debug(nombre, valor):
    debug_guardar(f"NORMALIZAR::{nombre}", valor)


def _check(nombre, cond, detalle=None):
    debug_guardar(f"CHECK::NORMALIZAR::{nombre}", {
        "ok": bool(cond),
        "detalle": str(detalle)[:200]
    })


# ==========================================================
# HELPERS
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
        return [match.group(2).strip()] * int(match.group(1))

    return [token]


def _split_bloques(texto: str):

    if texto is None:
        return []

    texto = texto.replace(";", ",").replace("|", ",")

    partes = re.split(r"[,\n]+", texto)

    return [p.strip() for p in partes if p.strip()]


def expandir_lista_codigos(texto: str):

    _debug("raw_texto", texto)

    if texto is None:
        return []

    texto = str(texto).upper()

    texto = re.sub(r"\{[^:]*:", "", texto)
    texto = texto.replace("{", "").replace("}", "")
    texto = texto.replace("\\P", ",")

    partes = _split_bloques(texto)

    resultado = []

    for p in partes:
        tokens = _expandir_multiplicador(p)

        for t in tokens:
            codigo = limpiar_codigo(t)
            if codigo:
                resultado.append(codigo)

    _debug("codigos_expandidos", resultado)

    return resultado


# ==========================================================
# CORE
# ==========================================================

def _convertir_a_largo(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()
    df.columns = df.columns.str.strip()

    _debug("input_columnas", list(df.columns))
    _debug("input_shape", df.shape)

    registros = []

    for idx, row in df.iterrows():

        # ==================================================
        # PUNTO
        # ==================================================
        punto = row.get("Punto") or row.get("punto") or f"P-{idx+1}"

        # ==================================================
        # DETECTAR COLUMNA DE ESTRUCTURA
        # ==================================================
        estructura_raw = None

        for col in df.columns:
            col_norm = col.lower().replace(" ", "")

            if col_norm in ["estructura", "estructuras", "codigodeestructura"]:
                estructura_raw = row.get(col)
                break

        # 🔴 DEBUG SI NO ENCUENTRA
        if estructura_raw is None:
            _debug(f"fila_{idx}_sin_estructura", dict(row))
            continue

        # ==================================================
        # EXPANDIR
        # ==================================================
        lista_codigos = expandir_lista_codigos(estructura_raw)

        _debug(f"fila_{idx}_codigos", lista_codigos)

        # ==================================================
        # CREAR REGISTROS
        # ==================================================
        for cod in lista_codigos:

            cod = limpiar_codigo(cod)

            if not cod:
                continue

            registros.append({
                "punto": str(punto).strip(),

                # 🔥 FIX CRÍTICO (NO TOCAR)
                "codigodeestructura": cod,
                "Estructura": cod,

                "cantidad": 1
            })

    # ==================================================
    # DATAFRAME FINAL
    # ==================================================
    df_out = pd.DataFrame(registros)

    # 🔥 DEBUG CLAVE (esto te dirá si funciona)
    _debug("output_columnas", list(df_out.columns))
    _debug("output_shape", df_out.shape)

    _check("output_no_vacio", not df_out.empty, len(df_out))

    return df_out

# ==========================================================
# FUNCIÓN PÚBLICA
# ==========================================================
def normalizar_estructuras(df: pd.DataFrame):

    try:
        df_norm = _convertir_a_largo(df)

        return df_norm, [], []

    except Exception as e:

        _debug("error", str(e))

        return pd.DataFrame(), [str(e)], []
