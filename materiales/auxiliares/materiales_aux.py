# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from collections import Counter
from ayuda.debug import debug_guardar


# ==========================================================
# HELPERS
# ==========================================================
def _limpiar_str(v) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _es_proyectado(bloque: str) -> bool:
    if bloque is None:
        return False
    return "(P)" in bloque.upper()


def _expandir_multiplicador(token: str):
    """
    Ej: "2xB-III-1" → ["B-III-1", "B-III-1"]
    """
    token = token.strip()

    match = re.match(r"(\d+)\s*[xX]\s*(.+)", token)
    if match:
        n = int(match.group(1))
        val = match.group(2).strip()
        return [val] * n

    return [token]


def _split_bloques(texto: str):
    """
    Divide bloques por coma o salto de línea
    """
    if texto is None:
        return []

    texto = texto.replace(";", ",")
    texto = texto.replace("|", ",")

    partes = re.split(r"[,\n]", texto)

    return [p.strip() for p in partes if p.strip()]


# ==========================================================
# LIMPIEZA FINAL DE CÓDIGO (🔥 CRÍTICO)
# ==========================================================
def limpiar_codigo(codigo: str) -> str:
    """
    Normaliza un código SIN destruir su estructura
    """

    if codigo is None:
        return ""

    codigo = str(codigo).strip().upper()

    if not codigo:
        return ""

    # 🔥 eliminar contenido entre paréntesis
    codigo = re.sub(r"\(.*?\)", "", codigo)

    # 🔥 eliminar espacios
    codigo = re.sub(r"\s+", "", codigo)

    # 🔥 limpieza NO destructiva
    codigo = re.sub(r"[^A-Z0-9\-\.\+]", "", codigo)

    return codigo


# ==========================================================
# FUNCIÓN CENTRAL
# ==========================================================
def expandir_lista_codigos(texto: str):
    """
    Convierte texto DXF sucio en lista limpia de estructuras

    Ej:
    "{C7:P-08,PC-30 (P),B-III-1 (P),LL-1-50W (P)}"

    → ["PC-30", "B-III-1", "LL-1-50W"]
    """

    debug_guardar("raw_texto_entrada", texto)

    if texto is None:
        return []

    texto = str(texto).upper()

    # ======================================================
    # 1. LIMPIEZA DXF
    # ======================================================

    # eliminar encabezados tipo {C7:
    texto = re.sub(r"\{[^:]*:", "", texto)

    # eliminar llaves
    texto = texto.replace("{", "").replace("}", "")

    # eliminar saltos DXF
    texto = texto.replace("\\P", ",")

    # ======================================================
    # 2. LIMPIEZA CONTROLADA
    # ======================================================

    # eliminar (P), (E), etc
    texto = re.sub(r"\([^)]*\)", "", texto)

    # normalizar separadores
    texto = texto.replace(";", ",")
    texto = texto.replace("|", ",")

    # limpiar espacios
    texto = re.sub(r"\s+", " ", texto).strip()

    debug_guardar("texto_limpio", texto)

    # ======================================================
    # 3. DIVISIÓN
    # ======================================================
    partes = _split_bloques(texto)

    resultado = []

    for p in partes:

        if not p:
            continue

        # expandir multiplicadores
        tokens = _expandir_multiplicador(p)

        for t in tokens:
            t = t.strip()

            if not t:
                continue

            codigo = limpiar_codigo(t)

            if not codigo:
                continue

            resultado.append(codigo)

    debug_guardar("codigos_expandidos", resultado)

    return resultado


# ==========================================================
# EXPANSIÓN + CONTEO
# ==========================================================
def expandir_y_contar(texto: str):
    """
    Devuelve dict con conteo de estructuras
    """
    lista = expandir_lista_codigos(texto)

    conteo = Counter()

    for c in lista:
        conteo[c] += 1

    debug_guardar("conteo_estructuras", dict(conteo))

    return dict(conteo)


# ==========================================================
# VALIDACIÓN
# ==========================================================
def validar_codigos(lista_codigos):
    """
    Valida lista de códigos
    """

    errores = []

    for c in lista_codigos:
        if not isinstance(c, str) or not c.strip():
            errores.append(f"Código inválido: {c}")

    debug_guardar("errores_codigos", errores)

    return errores
