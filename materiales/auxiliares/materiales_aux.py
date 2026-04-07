# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from collections import Counter
from ayuda.debug import debug_guardar


# ==========================================================
# HELPERS
# ==========================================================
def _limpiar_str(v) -> str:
    return "" if v is None else str(v).strip()


def _es_proyectado(bloque: str) -> bool:
    return "(P)" in str(bloque).upper() if bloque else False


# ==========================================================
# EXPANSIÓN MULTIPLICADOR
# ==========================================================
def _expandir_multiplicador(token: str):

    if not token:
        return []

    token = token.strip().upper()
    debug_guardar("EXPANDIR_INPUT", token)

    # caso: 2 x B-III-1
    match = re.match(r"^\s*(\d+)\s*[xX]\s*(.+)$", token)
    if match:
        n = int(match.group(1))
        val = match.group(2).strip()
        debug_guardar("EXPANDIR_MATCH_1", {"n": n, "val": val})
        return [val] * n

    # caso: 3XCS-2
    match = re.match(r"^\s*(\d+)[xX]([A-Z0-9\-\.\+]+)$", token)
    if match:
        n = int(match.group(1))
        val = match.group(2).strip()
        debug_guardar("EXPANDIR_MATCH_2", {"n": n, "val": val})
        return [val] * n

    return [token]


# ==========================================================
# SPLIT CONTROLADO
# ==========================================================
def _split_bloques(texto: str):

    if texto is None:
        return []

    texto = texto.replace(";", ",")
    texto = texto.replace("|", ",")
    texto = texto.replace("\\P", ",")

    debug_guardar("SPLIT_TEXTO_IN", texto)

    partes = re.split(r"[,\n]+", texto)

    resultado = []
    buffer = None

    for p in partes:
        p = p.strip()

        if not p:
            continue

        # detecta "3 X"
        if re.match(r"^\d+\s*[xX]$", p):
            buffer = p
            continue

        if buffer:
            p = f"{buffer} {p}"
            buffer = None

        resultado.append(p)

    debug_guardar("SPLIT_RESULTADO", resultado)

    return resultado


# ==========================================================
# LIMPIEZA FINAL (CORREGIDA)
# ==========================================================
def limpiar_codigo(codigo: str) -> str:

    if codigo is None:
        return ""

    codigo_original = codigo

    codigo = str(codigo).strip().upper()

    # eliminar (P)
    codigo = re.sub(r"\(.*?\)", "", codigo)

    # ⚠️ NO eliminar espacios internos
    codigo = codigo.strip()

    # eliminar basura pero conservar estructura
    codigo = re.sub(r"[^A-Z0-9\-\.\+ ]", "", codigo)

    debug_guardar("LIMPIAR_CODIGO", {
        "input": codigo_original,
        "output": codigo
    })

    return codigo


# ==========================================================
# FUNCIÓN CENTRAL
# ==========================================================
def expandir_lista_codigos(texto: str):

    debug_guardar("RAW_TEXTO", texto)

    if texto is None:
        return []

    texto = str(texto).upper()

    # limpieza DXF
    texto = re.sub(r"\{[^:]*:", "", texto)
    texto = texto.replace("{", "").replace("}", "")

    debug_guardar("TEXTO_LIMPIO", texto)

    partes = _split_bloques(texto)

    resultado = []

    for p in partes:

        if not p:
            continue

        # 🔥 DEBUG CRÍTICO
        if "CS" in p:
            debug_guardar("DEBUG_CS_PARTE", p)

        # quitar (P)
        p = re.sub(r"\(.*?\)", "", p)

        tokens = _expandir_multiplicador(p)

        for t in tokens:

            if "CS" in t:
                debug_guardar("DEBUG_CS_TOKEN", t)

            t = t.strip()

            if not t:
                continue

            codigo = limpiar_codigo(t)

            if "CS" in codigo:
                debug_guardar("DEBUG_CS_FINAL", codigo)

            # 🔥 VALIDACIÓN FUERTE (evita basura)
            if not re.match(r"^[A-Z]+-\d+[A-Z]*$", codigo):
                continue

            resultado.append(codigo)

    debug_guardar("CODIGOS_FINALES", resultado)

    return resultado


# ==========================================================
# EXPANSIÓN + CONTEO
# ==========================================================
def expandir_y_contar(texto: str):

    lista = expandir_lista_codigos(texto)

    conteo = Counter()

    for c in lista:
        conteo[c] += 1

    debug_guardar("CONTEO_FINAL", dict(conteo))

    return dict(conteo)


# ==========================================================
# VALIDACIÓN
# ==========================================================
def validar_codigos(lista_codigos):

    errores = []

    for c in lista_codigos:
        if not isinstance(c, str) or not c.strip():
            errores.append(f"Código inválido: {c}")

    debug_guardar("ERRORES_CODIGOS", errores)

    return errores
