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

    codigo = str(codigo).upper().strip()

    if not codigo:
        return ""

    # quitar paréntesis
    codigo = re.sub(r"\(.*?\)", "", codigo)

    # normalizar separadores
    codigo = codigo.replace(",", "")        # 2,000 → 2000
    codigo = codigo.replace(" ", "-")       # espacios → guión

    # eliminar basura pero conservar estructura
    codigo = re.sub(r"[^A-Z0-9\-]", "", codigo)

    # limpiar múltiples guiones
    codigo = re.sub(r"-+", "-", codigo)

    # quitar guiones extremos
    codigo = codigo.strip("-")

    return codigo


# ==========================================================
# NORMALIZACIÓN AUXILIAR
# ==========================================================
def _resolver_catalogo(codigo: str) -> str:
    if codigo.startswith("LL-"):
        if re.search(r"LL-\d+-.*W", codigo):
            return codigo
        return f"{codigo}-50W"

    return codigo


# ==========================================================
# VALIDACIÓN DE CÓDIGOS
# ==========================================================
def _es_codigo_valido(codigo: str) -> bool:
    if not codigo:
        return False

    if not re.search(r"\d", codigo):
        return False

    if len(codigo) < 3:
        return False

    return True


# ==========================================================
# 🔥 PARSER CORREGIDO
# ==========================================================
def _extraer_estructuras_general(texto: str) -> list[str]:
    if not texto:
        return []

    texto = texto.upper()

    texto = (
        texto.replace(",", "")
        .replace(";", " ")
        .replace("/", " ")
        .replace("|", " ")
    )

    # ✅ NUEVO PATRÓN (CLAVE)
    # Captura correctamente:
    # A-I-1
    # B-III-4C
    # TS-50KVA
    # PC-40
    patron = r"\b[A-Z]+(?:-[A-Z0-9]+)+\b"

    return re.findall(patron, texto)


# ==========================================================
# CORE
# ==========================================================
def _convertir_a_largo(df: pd.DataFrame) -> pd.DataFrame:

    registros = []
    debug_detectados = []

    for idx, row in df.iterrows():

        texto = " ".join([str(v) for v in row.values if pd.notna(v)])

        if not texto:
            continue

        texto = texto.upper().replace("(P)", "")

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
            # EXTRAER ESTRUCTURAS
            # -------------------------------------------------
            encontrados = _extraer_estructuras_general(linea)

            debug_detectados.append({
                "linea": linea,
                "detectados": encontrados
            })

            for e in encontrados:

                est = limpiar_codigo(e)
                est = _resolver_catalogo(est)

                if not _es_codigo_valido(est):
                    continue

                registros.append({
                    "Punto": punto_actual if punto_actual else f"P-{idx+1}",
                    "codigodeestructura": est,
                    "Cantidad": 1
                })

    df_out = pd.DataFrame(registros)

    if df_out.empty:
        return df_out

    df_out = (
        df_out
        .groupby(["Punto", "codigodeestructura"], as_index=False)["Cantidad"]
        .sum()
    )

    df_out.attrs["debug_parser"] = debug_detectados

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
