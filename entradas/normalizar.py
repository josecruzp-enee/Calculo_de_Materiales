# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import pandas as pd


# ==========================================================
# API (usado por otros módulos)
# ==========================================================
def limpiar_codigo(codigo: str) -> str:
    if codigo is None:
        return ""

    codigo = str(codigo).strip().upper()
    if not codigo:
        return ""

    codigo = re.sub(r"\(.*?\)", "", codigo)     # quitar paréntesis
    codigo = codigo.replace(" ", "")
    codigo = re.sub(r"[^A-Z0-9\-\.\+]", "", codigo)

    return codigo


# ==========================================================
# NORMALIZACIÓN AUXILIAR
# ==========================================================
def _resolver_catalogo(codigo: str) -> str:
    """
    Ajustes puntuales (ej: luminarias)
    """
    if codigo.startswith("LL-"):
        if re.search(r"LL-\d+-\d+W", codigo):
            return codigo
        return f"{codigo}-50W"

    return codigo


# ==========================================================
# PARSER GENERAL (CLAVE)
# ==========================================================
def _extraer_estructuras_general(texto: str) -> list[str]:
    """
    Parser flexible:
    - Detecta candidatos
    - NO valida (eso es otro módulo)
    """

    if not texto:
        return []

    texto = texto.upper()

    # Separadores comunes
    texto = (
        texto.replace(",", " ")
        .replace(";", " ")
        .replace("/", " ")
        .replace("|", " ")
    )

    # Patrón general (soporta todos tus casos reales)
    patron = r"\b[A-Z]{1,4}[-\s]?[A-Z0-9]+(?:[-\s]?[A-Z0-9]+)*\b"

    return re.findall(patron, texto)


# ==========================================================
# CORE
# ==========================================================
def _convertir_a_largo(df: pd.DataFrame) -> pd.DataFrame:

    registros = []

    for idx, row in df.iterrows():

        texto = " ".join([str(v) for v in row.values if pd.notna(v)])

        if not texto:
            continue

        texto = texto.upper().replace("(P)", "")

        # dividir en líneas lógicas
        lineas = re.split(r"\n|\\P|;", texto)

        punto_actual = None

        for linea in lineas:

            linea = linea.strip()
            if not linea:
                continue

            # -------------------------------------------------
            # DETECTAR POSTE (P-XX)
            # -------------------------------------------------
            m_poste = re.match(r"P[-\s]?(\d+)", linea)

            if m_poste:
                num = m_poste.group(1)
                punto_actual = f"P-{num}"
                continue

            # -------------------------------------------------
            # EXTRAER ESTRUCTURAS (FLEXIBLE)
            # -------------------------------------------------
            encontrados = _extraer_estructuras_general(linea)

            for e in encontrados:

                est = limpiar_codigo(e)
                est = _resolver_catalogo(est)

                if not est:
                    continue

                registros.append({
                    "Punto": punto_actual if punto_actual else f"P-{idx+1}",
                    "codigodeestructura": est,
                    "Cantidad": 1
                })

    df_out = pd.DataFrame(registros)

    if df_out.empty:
        return df_out

    # -------------------------------------------------
    # AGRUPAR
    # -------------------------------------------------
    df_out = (
        df_out
        .groupby(["Punto", "codigodeestructura"], as_index=False)["Cantidad"]
        .sum()
    )

    return df_out


# ==========================================================
# FUNCIÓN PÚBLICA
# ==========================================================
def normalizar_estructuras(df: pd.DataFrame):

    if not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(), ["df inválido o vacío"], []

    try:
        df_norm = _convertir_a_largo(df)

        if df_norm.empty:
            return pd.DataFrame(), ["No se detectaron estructuras válidas"], []

        return df_norm, [], []

    except Exception as e:
        return pd.DataFrame(), [str(e)], []
