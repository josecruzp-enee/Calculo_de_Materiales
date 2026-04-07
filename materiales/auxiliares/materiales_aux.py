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

    if texto is None:
        return []

    texto = str(texto).upper().strip()

    if not texto:
        return []

    # =========================
    # LIMPIEZA BASE
    # =========================
    texto = re.sub(r"\{[^}]*?:", "", texto)  # elimina {C7:
    texto = texto.replace("}", "")
    texto = texto.replace(";", ",")
    texto = texto.replace("|", ",")

    # =========================
    # SPLIT SOLO POR COMA
    # =========================
    bloques = [b.strip() for b in texto.split(",") if b.strip()]

    resultado = []

    for b in bloques:

        # solo estructuras proyectadas
        if "(P)" not in b:
            continue

        # quitar (P)
        b = b.replace("(P)", "").strip()

        if not b:
            continue

        # limpiar código final
        b = limpiar_codigo(b)

        if b:
            resultado.append(b)

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
