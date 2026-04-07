# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from collections import Counter


# ==========================================================
# HELPERS
# ==========================================================

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
# FUNCIÓN CRÍTICA (FIX REAL)
# ==========================================================
def expandir_lista_codigos(texto: str):
    """
    🔥 FUNCIÓN CENTRAL DEL SISTEMA

    Convierte texto sucio tipo DXF:

    "{C7:P-08,PC-30 (P),B-III-1 (P),LL-1-50W (P)}"

    → ["PC-30", "B-III-1", "LL-1-50W"]
    """

    if texto is None:
        return []

    texto = str(texto).upper()

    # ======================================================
    # 1. LIMPIEZA DXF FUERTE
    # ======================================================

    # eliminar encabezados tipo {C7:
    texto = re.sub(r"\{[^:]*:", "", texto)

    # eliminar llaves
    texto = texto.replace("{", "").replace("}", "")

    # eliminar saltos DXF
    texto = texto.replace("\\P", ",")

    # ======================================================
    # 2. LIMPIEZA DE TEXTO
    # ======================================================

    # eliminar (P), (E), etc
    texto = re.sub(r"\([^)]*\)", "", texto)

    # eliminar etiquetas tipo P-01
    texto = re.sub(r"\bP-\d+\b", "", texto)

    # normalizar separadores
    texto = texto.replace(";", ",")
    texto = texto.replace("|", ",")

    # eliminar espacios duplicados
    texto = re.sub(r"\s+", " ", texto).strip()

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

            # limpiar código final
            codigo = limpiar_codigo(t)

            if not codigo:
                continue

            resultado.append(codigo)

    return resultado


# ==========================================================
# LIMPIEZA FINAL DE CÓDIGO
# ==========================================================
def limpiar_codigo(codigo: str) -> str:
    """
    Normaliza un código individual
    """

    if codigo is None:
        return ""

    codigo = str(codigo).strip().upper()

    if not codigo:
        return ""

    # eliminar espacios internos raros
    codigo = re.sub(r"\s+", "", codigo)

    # eliminar caracteres no válidos al final
    codigo = re.sub(r"[^\w\-\.]", "", codigo)

    return codigo


# ==========================================================
# EXPANSIÓN + CONTEO
# ==========================================================
def expandir_y_contar(texto: str):
    """
    Devuelve dict con conteo
    """
    lista = expandir_lista_codigos(texto)

    conteo = Counter()

    for c in lista:
        conteo[c] += 1

    return dict(conteo)


# ==========================================================
# VALIDACIÓN (OPCIONAL)
# ==========================================================
def validar_codigos(lista_codigos):
    """
    Valida lista de códigos
    """

    errores = []

    for c in lista_codigos:
        if not isinstance(c, str) or not c.strip():
            errores.append(f"Código inválido: {c}")

    return errores
