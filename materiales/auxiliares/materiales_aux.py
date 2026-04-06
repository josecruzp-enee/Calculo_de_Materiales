# -*- coding: utf-8 -*-
"""
materiales_aux.py

Funciones auxiliares para:
- limpieza de códigos
- expansión de estructuras
- normalización base

🔥 CRÍTICO: aquí se separan correctamente los códigos
"""

from __future__ import annotations
import re


# ==========================================================
# LIMPIAR CÓDIGO INDIVIDUAL
# ==========================================================
def limpiar_codigo(codigo: str) -> str:
    """
    Normaliza un código de estructura.

    Ej:
        " a-iii-1 " → "A-III-1"
        "TS-37.5 KVA" → "TS-37.5KVA"
    """

    if codigo is None:
        return ""

    codigo = str(codigo).strip().upper()

    if not codigo:
        return ""

    # eliminar paréntesis
    codigo = re.sub(r"\(.*?\)", "", codigo)

    # normalizar espacios
    codigo = re.sub(r"\s+", " ", codigo).strip()

    # =========================
    # CASO ESPECIAL: TRANSFORMADORES
    # =========================
    # TS-37.5 KVA → TS-37.5KVA
    codigo = codigo.replace(" KVA", "KVA")

    return codigo


# ==========================================================
# EXPANDIR LISTA DE CÓDIGOS
# ==========================================================
def expandir_lista_codigos(texto: str) -> list[str]:
    """
    Convierte un string en lista de códigos de estructuras.

    SOPORTA:
        ✔ "A-I-1, B-II-3"
        ✔ "A-I-1 B-II-3"
        ✔ "A-I-1;B-II-3"
        ✔ "CA-2A CA-32A"  ← FIX CRÍTICO

    NO rompe:
        ✔ TS-37.5KVA
    """

    if texto is None:
        return []

    texto = str(texto).strip().upper()

    if not texto:
        return []

    # =========================
    # LIMPIEZA BASE
    # =========================
    texto = texto.replace("(", "").replace(")", "")
    texto = texto.replace(";", ",")
    texto = texto.replace("|", ",")

    # normalizar espacios múltiples
    texto = re.sub(r"\s+", " ", texto)

    # =========================
    # SEPARACIÓN PRINCIPAL
    # =========================
    bloques = texto.split(",")

    codigos = []

    for bloque in bloques:
        bloque = bloque.strip()

        if not bloque:
            continue

        # dividir por espacio
        partes = bloque.split(" ")

        for parte in partes:
            parte = parte.strip()

            if not parte:
                continue

            codigos.append(parte)

    # =========================
    # LIMPIEZA FINAL
    # =========================
    resultado = []

    for c in codigos:
        c = limpiar_codigo(c)

        if not c:
            continue

        resultado.append(c)

    return resultado


# ==========================================================
# EXPANDIR LISTA CON CONTEO
# ==========================================================
def expandir_y_contar(texto: str) -> dict[str, int]:
    """
    Retorna conteo de estructuras en un string.

    Ej:
        "A-I-1 A-I-1 B-II-3"
        →
        {
            "A-I-1": 2,
            "B-II-3": 1
        }
    """

    lista = expandir_lista_codigos(texto)

    conteo = {}

    for cod in lista:
        conteo[cod] = conteo.get(cod, 0) + 1

    return conteo


# ==========================================================
# VALIDAR CÓDIGOS CONTRA CATÁLOGO
# ==========================================================
def validar_codigos(codigos: list[str], catalogo: set[str]) -> tuple[list[str], list[str]]:
    """
    Valida qué códigos existen y cuáles no.

    Retorna:
        validos, no_encontrados
    """

    validos = []
    no_encontrados = []

    for c in codigos:
        if c in catalogo:
            validos.append(c)
        else:
            no_encontrados.append(c)

    return validos, no_encontrados


# ==========================================================
# TEST RÁPIDO (DEBUG)
# ==========================================================
if __name__ == "__main__":

    casos = [
        "CA-2A CA-32A",
        "A-I-1, B-II-3",
        "TS-37.5 KVA",
        "A-I-1;B-II-3",
        "  a-iii-1   b-iii-5  ",
    ]

    for c in casos:
        print("INPUT :", c)
        print("OUTPUT:", expandir_lista_codigos(c))
        print("-" * 40)
