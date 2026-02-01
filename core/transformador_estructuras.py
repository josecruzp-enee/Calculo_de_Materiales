# core/transformador_estructuras.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional, Tuple
import re
import pandas as pd


def coerce_df_estructuras_largo(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte/normaliza la tabla de estructuras a formato largo (long) con contrato CORE:

        - Punto (str)
        - codigodeestructura (str)
        - cantidad (int)

    Acepta:
      A) Ya en largo: ['Punto', 'codigodeestructura', 'cantidad'] (o variaciones)
      B) Ancho clásico: 'Punto' + columnas que SON códigos (valores = cantidad)
      C) Columna "Estructuras" con códigos separados por coma/; (cantidad implícita = 1)
      B+) Columnas por categoría (Primario/Secundario/Transformadores/...) con TEXTO dentro
          de cada celda: "A-III-1, A-I-4; CT-N x2" etc.

    Regresa DataFrame largo listo para cálculo.
    """
    if df is None or not isinstance(df, pd.DataFrame):
        return pd.DataFrame(columns=["Punto", "codigodeestructura", "cantidad"])

    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]

    if out.empty:
        return pd.DataFrame(columns=["Punto", "codigodeestructura", "cantidad"])

    # -------- helpers --------
    cols_lower = {c.lower().strip(): c for c in out.columns}

    def _find_col(*cands: str) -> Optional[str]:
        for cand in cands:
            cand2 = cand.lower().strip().replace(" ", "").replace("_", "")
            for k, orig in cols_lower.items():
                k2 = k.replace(" ", "").replace("_", "")
                if k == cand.lower().strip() or k2 == cand2:
                    return orig
        return None

    # Detectar columna de Punto
    c_punto = _find_col("Punto", "Puntos", "Nodo", "Nodos", "Estructura Punto")

    # OJO: NO usar "Poste" como Punto: en tu DF real "Poste" es una categoría.
    # Si no hay Punto explícito, usamos la primera columna como Punto (fallback)
    if not c_punto and len(out.columns) >= 1:
        c_punto = out.columns[0]

    # Detectar si ya viene largo
    c_cod = _find_col("codigodeestructura", "codigoestructura", "codigo de estructura", "estructura", "codigo", "cod")
    c_cant = _find_col("cantidad", "cant", "qty", "cantidad (p)", "cantidad_p", "n")

    if c_punto and c_cod and c_cant:
        df_long = out[[c_punto, c_cod, c_cant]].copy()
        df_long = df_long.rename(columns={c_punto: "Punto", c_cod: "codigodeestructura", c_cant: "cantidad"})
        return _postprocesar_largo(df_long)

    # Caso C: columna "Estructuras" con texto
    c_estructs = _find_col("Estructuras", "Estructura", "Códigos", "Codigos", "Codigos de estructura")
    if c_estructs and c_punto:
        tmp = out[[c_punto, c_estructs]].copy()
        tmp = tmp.rename(columns={c_punto: "Punto"})

        # explotar por separadores comunes
        tmp["codigodeestructura"] = tmp[c_estructs].astype(str).apply(_split_codigos)
        tmp = tmp.explode("codigodeestructura")

        # cantidad por defecto 1, pero si el token trae "x2" lo respetamos
        tmp[["codigodeestructura", "cantidad"]] = tmp["codigodeestructura"].apply(_parse_token).apply(pd.Series)

        tmp = tmp[["Punto", "codigodeestructura", "cantidad"]]
        return _postprocesar_largo(tmp)

    # ---------------------------------------------------------------------------------
    # Caso B+: columnas por categoría (Primario/Secundario/Transformadores/...) con texto
    # ---------------------------------------------------------------------------------
    if c_punto:
        id_col = c_punto
        value_cols = [c for c in out.columns if c != id_col]

        # Detectar si en general hay texto "tipo códigos" en las celdas
        # (si hay, preferimos B+ antes que melt clásico)
        if value_cols and _parece_texto_en_celdas(out, value_cols):
            filas = []

            for _, row in out.iterrows():
                punto = str(row[id_col]).strip()
                if not punto:
                    continue

                for col in value_cols:
                    val = row[col]
                    if val is None:
                        continue

                    s = str(val).strip()
                    if not s or s.lower() in ("nan", "none"):
                        continue

                    # Separar múltiples códigos en una celda
                    tokens = _split_codigos(s)
                    for tok in tokens:
                        cod, cant = _parse_token(tok)
                        if cod:
                            filas.append({"Punto": punto, "codigodeestructura": cod, "cantidad": cant})

            return _postprocesar_largo(pd.DataFrame(filas))

    # ----------------------------
    # Caso B: ancho clásico (melt)
    # ----------------------------
    if c_punto:
        id_col = c_punto
        value_cols = [c for c in out.columns if c != id_col]
        if value_cols:
            melted = out.melt(
                id_vars=[id_col],
                value_vars=value_cols,
                var_name="codigodeestructura",
                value_name="cantidad",
            )
            melted = melted.rename(columns={id_col: "Punto"})
            return _postprocesar_largo(melted)

    # Si llegamos aquí, no pudimos inferir formato
    return pd.DataFrame(columns=["Punto", "codigodeestructura", "cantidad"])


def _postprocesar_largo(df_long: pd.DataFrame) -> pd.DataFrame:
    """Normalización final del contrato largo + filtrado de vacíos."""
    if df_long is None or df_long.empty:
        return pd.DataFrame(columns=["Punto", "codigodeestructura", "cantidad"])

    df = df_long.copy()

    for c in ["Punto", "codigodeestructura"]:
        if c not in df.columns:
            df[c] = ""
        df[c] = df[c].astype(str).str.strip()

    if "cantidad" not in df.columns:
        df["cantidad"] = 1

    df["codigodeestructura"] = df["codigodeestructura"].astype(str).str.strip().str.upper()
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0).astype(int)

    # Filtrar filas inválidas
    df = df[df["Punto"].str.len() > 0]
    df = df[df["codigodeestructura"].str.len() > 0]
    df = df[df["cantidad"] > 0]

    # Orden + columnas finales
    df = df[["Punto", "codigodeestructura", "cantidad"]].reset_index(drop=True)
    return df


# =============================================================================
# Helpers de parsing de texto (B+)
# =============================================================================

_SPLIT_RE = re.compile(r"[,\n;|]+")

# Códigos típicos de estructuras: A-I-4, B-III-4C, etc.
_COD_ESTRUCT_RE = re.compile(r"\b[A-Z]{1,3}-[IVX]{1,4}-\d+[A-Z]?\b")


def _split_codigos(s: str) -> list[str]:
    """
    Separa una celda con múltiples códigos.

    Acepta separadores: coma, punto y coma, salto de línea, pipe.
    Además, si un token trae 2+ códigos pegados por espacios (ej: "A-I-4 A-I-4V"),
    extrae los códigos con regex sin romper tokens válidos con espacios (ej: "TS-50 KVA").
    """
    if s is None:
        return []
    s = str(s).strip()
    if not s or s.lower() in ("nan", "none"):
        return []

    # 1) split por separadores "fuertes"
    parts = [p.strip() for p in _SPLIT_RE.split(s) if p.strip()]
    if not parts:
        parts = [s]

    # 2) si algún token contiene múltiples códigos tipo A-I-4 separados por espacio,
    #    extraerlos con regex (evita partir "TS-50 KVA")
    out: list[str] = []
    for p in parts:
        p_up = p.upper().strip()

        matches = _COD_ESTRUCT_RE.findall(p_up)
        if len(matches) >= 2:
            out.extend(matches)
        else:
            out.append(p.strip())

    return out


def _parece_texto_en_celdas(df: pd.DataFrame, value_cols: list[str]) -> bool:
    """
    Heurística: si en una muestra de celdas hay strings con letras/guiones,
    asumimos que es el formato por categorías (B+).
    """
    # muestreamos pocas filas para no afectar rendimiento
    sample = df[value_cols].head(10)
    for col in value_cols:
        for v in sample[col].tolist():
            if isinstance(v, str):
                s = v.strip()
                if not s:
                    continue
                # si contiene letras o un guion típico de códigos
                if any(ch.isalpha() for ch in s) or "-" in s:
                    return True
    return False
