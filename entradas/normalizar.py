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

def extraer_multiplicador_estructura(codigo: str) -> tuple[int, str]:
    """
    Detecta estructuras con multiplicador al inicio.

    Ejemplos:
    3R-2      -> 3, R-2
    3R-2 (P)  -> 3, R-2
    2A-I-1    -> 2, A-I-1
    R-2       -> 1, R-2
    """

    if not codigo:
        return 1, ""

    texto = str(codigo).upper().strip()

    m = re.match(r"^(\d+)\s*([A-Z].*)$", texto)

    if not m:
        return 1, texto

    cantidad = int(m.group(1))
    estructura = m.group(2).strip()

    return cantidad, estructura
    
# =========================================================
# PATRÓN
# =========================================================
PATRON = re.compile(
    r"""
    \b(A-[IVX]+-\d+[A-Z]?)\b|
    \b(B-[IVX]+-\d+[A-Z]?)\b|
    \b(G-[IVX]+-\d+[A-Z]?)\b|
    \b(ER-[IVX]+-\d+[A-Z]?)\b|
    \b(CS-\d+)\b|
    \b(CA-\d+)\b|
    \b(P[CMT][A-Z]?-\d+)\b|
    \b(T[ST]-\d+(?:\.\d+)?KVA)\b|
    \b(CT-[A-Z])\b|
    \b(R-\d+[A-Z]?)\b|
    \b(LL-\d+(?:-[0-9A-Z]+)+)\b
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

            try:
                debug_guardar("WARNING_SIN_PUNTO", {
                    "fila": idx,
                    "texto": texto_upper
                })
            except:
                pass

        # =====================================================
        # TOKENIZAR
        # Soporta:
        # R-2 (P)
        # 3R-2 (P)
        # 2A-I-1 (P)
        # =====================================================
        tokens = re.findall(r'\S+(?:\s*\([EPDR]\))?', texto_upper)

        for token in tokens:

            m_tipo = re.search(r'\((P|D|E|R)\)', token)

            # =====================================================
            # 🔥 SOPORTE DXF + MANUAL
            # =====================================================
            if m_tipo:
                # DXF: solo proyectado
                if m_tipo.group(1) != "P":
                    continue

                est_raw = re.sub(r'\s*\([EPDR]\)', '', token)
            else:
                # Manual: aceptar directo
                est_raw = token

            # =====================================================
            # 🔥 MULTIPLICADOR
            # 3R-2 -> cantidad 3, estructura R-2
            # R-2  -> cantidad 1, estructura R-2
            # =====================================================
            cantidad = 1

            m_mult = re.match(r"^(\d+)([A-Z].*)$", est_raw.strip())

            if m_mult:
                cantidad = int(m_mult.group(1))
                est_raw = m_mult.group(2).strip()

            est = limpiar_codigo(est_raw)

            if not est:
                continue

            if not PATRON.match(est):
                continue

            registros.append({
                "Punto": punto_actual,
                "Estructura": est,
                "Cantidad": cantidad
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
        import traceback

        debug_guardar("DXF_EXCEPTION", {
            "error": str(e),
            "traceback": traceback.format_exc()
        })

        raise
