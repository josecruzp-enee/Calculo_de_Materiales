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
# 🔥 RESOLUCIÓN DE CATÁLOGO
# ==========================================================
def resolver_codigo_catalogo(codigo: str) -> str:
    codigo = codigo.strip().upper()

    # =========================================
    # LUMINARIAS
    # =========================================
    if codigo.startswith("LL-"):
        if re.search(r"LL-\d+-\d+W", codigo):
            return codigo
        return f"{codigo}-50W"

    return codigo


# ==========================================================
# EXPANSIÓN
# ==========================================================
def _expandir_multiplicador(token: str):

    if not token:
        return []

    token = token.strip().upper()

    match = re.match(r"^\s*(\d+)\s*[xX]\s*(.+)$", token)
    if match:
        return [match.group(2).strip()] * int(match.group(1))

    return [token]


# ==========================================================
# 🔥 SPLIT CORRECTO PARA DXF
# ==========================================================
def _split_bloques(texto: str):

    if texto is None:
        return []

    # 🔥 Unificar TODOS los separadores a salto de línea
    texto = texto.replace("\\P", "\n")   # AutoCAD
    texto = texto.replace(",", "\n")     # 🔥 CLAVE (tu caso actual)
    texto = texto.replace(";", "\n")
    texto = texto.replace("|", "\n")

    # limpiar duplicados
    texto = re.sub(r"\n+", "\n", texto)

    partes = texto.split("\n")

    return [p.strip() for p in partes if p.strip()]


# ==========================================================
# EXPANDIR LISTA
# ==========================================================
def expandir_lista_codigos(texto: str):

    _debug("raw_texto", texto)

    if texto is None:
        return []

    texto = str(texto).upper()

    texto = re.sub(r"\{[^:]*:", "", texto)
    texto = texto.replace("{", "").replace("}", "")
    texto = texto.replace("\\P", "\n")

    partes = _split_bloques(texto)

    # 🔥 CLAVE: NO dividir por espacios
    resultado = []

    for p in partes:

        tokens = _expandir_multiplicador(p)

        for t in tokens:
            codigo = limpiar_codigo(t)

            if not codigo:
                continue

            # 🔥 FILTRO ANTI-BASURA (CS-32 fantasma)
            if codigo.startswith("CS-") and codigo not in {"CS-1", "CS-2"}:
                _debug("codigo_descartado", codigo)
                continue

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
        # PUNTO ORIGINAL
        # ==================================================
        punto_original = row.get("Punto") or row.get("punto") or f"P-{idx+1}"
        punto_original = str(punto_original).strip()

        # ==================================================
        # DETECTAR COLUMNA
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
        # EXPANDIR
        # ==================================================
        lista_codigos = expandir_lista_codigos(estructura_raw)

        _debug(f"fila_{idx}_codigos", lista_codigos)

        # ==================================================
        # CLASIFICAR
        # ==================================================
        poste = None
        estructuras = []

        for cod in lista_codigos:

            if re.match(r"^P-?\d+$", cod):
                numero = re.findall(r"\d+", cod)[0]
                poste = f"P-{numero}"
            else:
                estructuras.append(cod)

        # ==================================================
        # PUNTO FINAL
        # ==================================================
        punto_final = poste if poste else punto_original

        # ==================================================
        # RESOLUCIÓN FINAL
        # ==================================================
        for est in estructuras:

            est_final = resolver_codigo_catalogo(est)

            _debug("resolver_codigo", {
                "original": est,
                "final": est_final
            })

            registros.append({
                "Punto": punto_final,
                "codigodeestructura": est_final,
                "Estructura": est_final,
                "cantidad": 1
            })

    # ==================================================
    # OUTPUT
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
