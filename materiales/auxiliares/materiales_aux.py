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

    debug_guardar("F1_EXPANDIR_INPUT", token)

    if not token:
        return []

    token = token.strip().upper()

    # caso: 2 x B-III-1
    match = re.match(r"^\s*(\d+)\s*[xX]\s*(.+)$", token)
    if match:
        n = int(match.group(1))
        val = match.group(2).strip()
        debug_guardar("F1_MATCH_ESPACIADO", {"n": n, "val": val})
        return [val] * n

    # caso: 3XCS-2
    match = re.match(r"^\s*(\d+)[xX]([A-Z0-9\-\.\+]+)$", token)
    if match:
        n = int(match.group(1))
        val = match.group(2).strip()
        debug_guardar("F1_MATCH_DIRECTO", {"n": n, "val": val})
        return [val] * n

    return [token]


# ==========================================================
# SPLIT CONTROLADO
# ==========================================================
def _split_bloques(texto: str):

    debug_guardar("F2_SPLIT_ENTRADA", texto)

    if texto is None:
        return []

    texto = texto.replace(";", ",")
    texto = texto.replace("|", ",")
    texto = texto.replace("\\P", ",")

    partes = re.split(r"[,\n]+", texto)

    resultado = []
    buffer = None

    for p in partes:
        p = p.strip()

        if not p:
            continue

        if re.match(r"^\d+\s*[xX]$", p):
            buffer = p
            continue

        if buffer:
            p = f"{buffer} {p}"
            buffer = None

        resultado.append(p)

    debug_guardar("F2_SPLIT_RESULTADO", resultado)

    return resultado


# ==========================================================
# LIMPIEZA FINAL
# ==========================================================
def limpiar_codigo(codigo: str) -> str:

    debug_guardar("F3_LIMPIAR_INPUT", codigo)

    if codigo is None:
        return ""

    codigo_original = codigo

    codigo = str(codigo).strip().upper()

    # eliminar (P)
    codigo = re.sub(r"\(.*?\)", "", codigo)

    # ⚠️ IMPORTANTE: NO eliminar espacios internos
    codigo = codigo.strip()

    # limpiar caracteres raros
    codigo = re.sub(r"[^A-Z0-9\-\.\+ ]", "", codigo)

    debug_guardar("F3_LIMPIAR_OUTPUT", {
        "input": codigo_original,
        "output": codigo
    })

    return codigo


# ==========================================================
# FUNCIÓN CENTRAL (FORENSE)
# ==========================================================
def expandir_lista_codigos(texto: str):

    debug_guardar("EVIDENCIA_1_TEXTO_ORIGINAL", texto)

    if texto is None:
        return []

    texto = str(texto).upper()

    # limpieza DXF
    texto = re.sub(r"\{[^:]*:", "", texto)
    texto = texto.replace("{", "").replace("}", "")
    texto = texto.replace("\\P", ",")

    debug_guardar("EVIDENCIA_1B_TEXTO_LIMPIO", texto)

    partes = _split_bloques(texto)

    resultado = []

    for p in partes:

        # 🔥 DEBUG CLAVE
        if "CS" in str(p) or re.search(r"\b\d+\b", str(p)):
            debug_guardar("EVIDENCIA_2_PARTES", p)

        if not p:
            continue

        # quitar (P)
        p = re.sub(r"\(.*?\)", "", p)

        tokens = _expandir_multiplicador(p)

        for t in tokens:

            if "CS" in str(t) or re.match(r"^\d+$", str(t)):
                debug_guardar("EVIDENCIA_3_TOKENS", t)

            if not t:
                continue

            t = t.strip()

            debug_guardar("EVIDENCIA_4_PRE_LIMPIEZA", t)

            codigo = limpiar_codigo(t)

            debug_guardar("EVIDENCIA_5_POST_LIMPIEZA", codigo)

            # 🔥 FILTRO CRÍTICO
            if re.match(r"^\d+$", codigo):
                debug_guardar("DESCARTADO_NUMERO", codigo)
                continue

            if not re.match(r"^[A-Z]+-\d+[A-Z]*$", codigo):
                debug_guardar("DESCARTADO_INVALIDO", codigo)
                continue

            resultado.append(codigo)

    debug_guardar("EVIDENCIA_6_RESULTADO_FINAL", resultado)

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
