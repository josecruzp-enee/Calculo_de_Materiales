# -*- coding: utf-8 -*-
"""
materiales_aux.py

Funciones auxiliares robustas y limpias para:
- limpieza de códigos
- expansión de estructuras
"""

from __future__ import annotations
import re


# ==========================================================
# LIMPIEZA BÁSICA
# ==========================================================
def limpiar_codigo(codigo: str) -> str:
    if not codigo:
        return ""

    c = str(codigo).upper().strip()

    c = re.sub(r"\(.*?\)", "", c)        # quitar (P), etc
    c = re.sub(r"\s+", " ", c).strip()   # espacios
    c = c.replace(" KVA", "KVA")         # TS-37.5 KVA → TS-37.5KVA

    # CA-32A → CA-32
    c = re.sub(r"(CA-\d+)[A-Z]+$", r"\1", c)

    return c


# ==========================================================
# EXTRAER BLOQUES (RESPETA COMAS)
# ==========================================================
def _split_bloques(texto: str) -> list[str]:
    texto = texto.replace(";", ",").replace("|", ",")
    return [b.strip() for b in texto.split(",") if b.strip()]


# ==========================================================
# FILTRAR SOLO (P)
# ==========================================================
def _es_proyectado(bloque: str) -> bool:
    return "(P)" in bloque.upper()


# ==========================================================
# EXPANDIR MULTIPLICADOR
# ==========================================================
def _expandir_multiplicador(bloque: str) -> list[str]:
    match = re.match(r"(\d+)\s*X\s*(.+)", bloque, re.IGNORECASE)

    if match:
        n = int(match.group(1))
        cod = match.group(2).strip()
        return [cod] * n

    return [bloque]


# ==========================================================
# FUNCIÓN PRINCIPAL
# ==========================================================
def expandir_lista_codigos(texto: str) -> list[str]:

    if not texto:
        return []

    texto = str(texto).upper()

    bloques = _split_bloques(texto)

    resultado = []

    for b in bloques:

        # solo proyectados
        if not _es_proyectado(b):
            continue

        # quitar etiquetas
        b = re.sub(r"\(.*?\)", "", b).strip()

        # expandir
        lista = _expandir_multiplicador(b)

        for c in lista:
            c = limpiar_codigo(c)

            if not c:
                continue

            # filtro basura
            if len(c) <= 2:
                continue

            resultado.append(c)

    return resultado


# ==========================================================
# CONTEO
# ==========================================================
def expandir_y_contar(texto: str) -> dict[str, int]:
    conteo = {}

    for c in expandir_lista_codigos(texto):
        conteo[c] = conteo.get(c, 0) + 1

    return conteo


# ==========================================================
# VALIDACIÓN
# ==========================================================
def validar_codigos(codigos: list[str], catalogo: set[str]) -> tuple[list[str], list[str]]:
    validos = []
    no_encontrados = []

    for c in codigos:
        (validos if c in catalogo else no_encontrados).append(c)

    return validos, no_encontrados


# ==========================================================
# TEST
# ==========================================================
if __name__ == "__main__":

    caso = "LL-1-50W (P), CA-32 (E), 3 x CS-2 (P), R-2 (D)"

    print(expandir_lista_codigos(caso))
    print(expandir_y_contar(caso))
