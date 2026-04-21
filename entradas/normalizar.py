# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import pandas as pd


# =========================================================
# LIMPIEZA DXF (CRÍTICO)
# =========================================================
def limpiar_texto_dxf(texto: str) -> str:

    if not texto:
        return ""

    texto = str(texto)

    # 🔥 eliminar formato DXF
    texto = re.sub(r"\{.*?;", "", texto)

    texto = texto.replace("{", "")
    texto = texto.replace("}", "")
    texto = texto.replace("\\P", " ")

    return texto


# =========================================================
# LIMPIEZA CÓDIGO
# =========================================================
def limpiar_codigo(codigo: str) -> str:

    if not codigo:
        return ""

    codigo = str(codigo).upper().strip()

    codigo = re.sub(r"\(.*?\)", "", codigo)
    codigo = codigo.replace(",", "")
    codigo = codigo.replace(" ", "-")

    codigo = re.sub(r"[^A-Z0-9\.\-]", "", codigo)
    codigo = re.sub(r"-+", "-", codigo)

    codigo = codigo.replace("-KVA", "KVA")

    return codigo.strip("-")


# =========================================================
# PATRÓN
# =========================================================
PATRON = re.compile(
    r"""
    \b(A-[IVX]+-\d+[A-Z]?)\b|
    \b(B-[IVX]+-\d+[A-Z]?)\b|
    \b(CS-\d+)\b|      
    \b(CA-\d+)\b|  
    \b(P[CMT][A-Z]?-\d+)\b|
    \b(TS-\d+(?:\.\d+)?KVA)\b|
    \b(CT-[A-Z])\b|
    \b(R-\d+[A-Z]?)\b|
    \b(LL-\d+(?:-\d+[A-Z]+)+)\b
    """,
    re.VERBOSE
)


# =========================================================
# CORE
# =========================================================
def _convertir(df: pd.DataFrame):

    registros = []
    punto_actual = None  # 🔥 estado del punto

    for idx, row in df.iterrows():

        texto = " ".join(str(v) for v in row.values if pd.notna(v))
        texto = limpiar_texto_dxf(texto)

        if not texto:
            continue

        texto_upper = texto.upper()

        # =====================================================
        # 🔥 DETECTAR PUNTO
        # =====================================================
        m_punto = re.search(r"\bP[-\s]?(\d+)\b", texto_upper)
        if m_punto:
            punto_actual = f"P-{m_punto.group(1)}"
            

        # =====================================================
        # ⚠ FALLBACK CONTROLADO
        # =====================================================
        if not punto_actual:
            punto_actual = f"SIN_PUNTO_{idx+1}"

            # 🔥 DEBUG DE ADVERTENCIA
            try:
                debug_guardar("WARNING_SIN_PUNTO", {
                    "fila": idx,
                    "texto": texto_upper
                })
            except:
                pass

        # =====================================================
        # TOKENIZAR
        # =====================================================
        tokens = re.findall(r'\S+(?:\s*\([EPDR]\))?', texto_upper)

        for token in tokens:

            m_tipo = re.search(r'\((P|D|E|R)\)', token)

            if not m_tipo:
                continue

            # SOLO PROYECTADO
            if m_tipo.group(1) != "P":
                continue

            est_raw = re.sub(r'\s*\([EPDR]\)', '', token)
            est = limpiar_codigo(est_raw)

            if not est:
                continue

            if not PATRON.match(est):
                continue

            registros.append({
                "Punto": punto_actual,
                "Estructura": est,
                "Cantidad": 1
            })

    df_out = pd.DataFrame(registros)

    if df_out.empty:
        return pd.DataFrame(columns=["Punto", "Estructura", "Cantidad"])

    return (
        df_out
        .groupby(["Punto", "Estructura"], as_index=False)["Cantidad"]
        .sum()
    )

# =========================================================
# API
# =========================================================
def normalizar_estructuras(df: pd.DataFrame):

    if not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(), ["df inválido o vacío"], []

    try:
        df_norm = _convertir(df)

        if df_norm.empty:
            return df_norm, ["No se detectaron estructuras"], []

        return df_norm, [], []

    except Exception as e:
        return pd.DataFrame(), [str(e)], []
