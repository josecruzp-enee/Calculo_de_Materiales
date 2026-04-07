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
    Soporta:
    - 2xB-III-1
    - 2 x B-III-1
    - 3XCS-2
    """

    if not token:
        return []

    token = token.strip().upper()

    # 🔥 CASO 1: "3 x CS-2" o "3xCS-2"
    match = re.match(r"^\s*(\d+)\s*[xX]\s*(.+)$", token)
    if match:
        n = int(match.group(1))
        val = match.group(2).strip()
        return [val] * n

    # 🔥 CASO 2: "3XCS-2" (pegado)
    match = re.match(r"^\s*(\d+)[xX]([A-Z0-9\-\.]+)$", token)
    if match:
        n = int(match.group(1))
        val = match.group(2).strip()
        return [val] * n
    debug_guardar("tokens_expandidos", tokens)
    return [token]

def _split_bloques(texto: str):
    """
    Divide SOLO por coma o salto de línea
    🔥 Mantiene juntos los multiplicadores tipo: "3 X CS-2"
    """
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

        # 🔥 Detecta "3 X" suelto
        if re.match(r"^\d+\s*[xX]$", p):
            buffer = p
            continue

        # 🔥 Si había buffer, lo une correctamente
        if buffer:
            p = f"{buffer} {p}"
            buffer = None

        resultado.append(p)
    debug_guardar("partes_split", partes)
    return resultado
# ==========================================================
# LIMPIEZA FINAL DE CÓDIGO (🔥 BLINDADA)
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

    # 🔥 eliminar (P), (E), etc
    codigo = re.sub(r"\(.*?\)", "", codigo)

    # 🔥 eliminar espacios PERO NO GUIONES
    codigo = codigo.replace(" ", "")

    # 🔥 PERMITIR:
    # letras, números, guiones, puntos (para TS-37.5KVA), W
    codigo = re.sub(r"[^A-Z0-9\-\.\+]", "", codigo)

    return codigo


# ==========================================================
# FUNCIÓN CENTRAL
# ==========================================================
def expandir_lista_codigos(texto: str):
    """
    Convierte texto DXF sucio en lista limpia de estructuras
    """

    debug_guardar("raw_texto_entrada", texto)

    if texto is None:
        return []

    texto = str(texto).upper()

    # ======================================================
    # 1. LIMPIEZA DXF
    # ======================================================

    texto = re.sub(r"\{[^:]*:", "", texto)
    texto = texto.replace("{", "").replace("}", "")
    texto = texto.replace("\\P", ",")

    # ======================================================
    # 🔥 IMPORTANTE: NO eliminar todo antes de separar
    # ======================================================

    debug_guardar("texto_pre_split", texto)

    # ======================================================
    # 2. DIVISIÓN PRIMERO
    # ======================================================
    partes = _split_bloques(texto)

    resultado = []

    for p in partes:

        if not p:
            continue

        # 🔥 eliminar (P) después de separar
        p = re.sub(r"\(.*?\)", "", p)

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
    errores = []

    for c in lista_codigos:
        if not isinstance(c, str) or not c.strip():
            errores.append(f"Código inválido: {c}")

    debug_guardar("errores_codigos", errores)

    return errores
