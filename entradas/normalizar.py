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


# ==========================================================
# 🔥 NUEVO: RESOLUCIÓN DE CATÁLOGO
# ==========================================================
def resolver_codigo_catalogo(codigo: str) -> str:
    """
    Convierte códigos incompletos o ambiguos en códigos válidos de catálogo.
    Esta función es CRÍTICA para evitar errores de lookup en materiales.
    """
    codigo = codigo.strip().upper()

    # =========================================
    # 🔥 LUMINARIAS (LL)
    # =========================================
    if codigo.startswith("LL-"):

        # ya viene completo (ej: LL-1-50W)
        if re.search(r"LL-\d+-\d+W", codigo):
            return codigo

        # viene incompleto (ej: LL-1)
        return f"{codigo}-50W"

    # =========================================
    # (FUTURO) OTROS CASOS
    # =========================================
    # if codigo.startswith("TS-"):
    #     ...

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

    partes_expandido = []
    for p in partes:
        subpartes = p.split()
        partes_expandido.extend(subpartes)

    partes = partes_expandido

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
        # PUNTO ORIGINAL (fallback)
        # ==================================================
        punto_original = row.get("Punto") or row.get("punto") or f"P-{idx+1}"
        punto_original = str(punto_original).strip()

        # ==================================================
        # DETECTAR COLUMNA DE ESTRUCTURA
        # ==================================================
        estructura_raw = None

        for col in df.columns:
            col_norm = col.lower().replace(" ", "")

            if col_norm in ["estructura", "estructuras", "codigodeestructura"]:
                estructura_raw = row.get(col)
                break

        if estructura_raw is None:
            _debug(f"fila_{idx}_sin_estructura", dict(row))
            continue

        # ==================================================
        # EXPANDIR CÓDIGOS
        # ==================================================
        lista_codigos = expandir_lista_codigos(estructura_raw)

        _debug(f"fila_{idx}_codigos", lista_codigos)

        # ==================================================
        # CLASIFICAR
        # ==================================================
        poste = None
        estructuras = []

        for cod in lista_codigos:
            cod = limpiar_codigo(cod)

            if not cod:
                continue

            if re.match(r"^P-?\d+$", cod):
                numero = re.findall(r"\d+", cod)[0]
                poste = f"P-{numero}"
            else:
                estructuras.append(cod)

        # ==================================================
        # DEFINIR PUNTO FINAL
        # ==================================================
        punto_final = poste if poste else punto_original

        # ==================================================
        # 🔥 RESOLUCIÓN FINAL DE CÓDIGOS
        # ==================================================
        for est in estructuras:

            est_limpio = limpiar_codigo(est)
            est_final = resolver_codigo_catalogo(est_limpio)

            _debug("resolver_codigo", {
                "original": est,
                "limpio": est_limpio,
                "final": est_final
            })

            registros.append({
                "Punto": punto_final,
                "codigodeestructura": est_final,
                "Estructura": est_final,
                "cantidad": 1
            })

    # ==================================================
    # DATAFRAME FINAL
    # ==================================================
    df_out = pd.DataFrame(registros)

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
