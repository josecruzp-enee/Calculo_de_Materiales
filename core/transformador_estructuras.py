# core/transformador_estructuras.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional
import pandas as pd


def coerce_df_estructuras_largo(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte/normaliza la tabla de estructuras a formato largo (long) con contrato CORE:

        - Punto (str)
        - codigodeestructura (str)
        - cantidad (int)

    Acepta:
      A) Ya en largo: columnas tipo ['Punto', 'codigodeestructura', 'cantidad'] (o variaciones)
      B) En ancho:   'Punto' + columnas de estructuras (cada columna = código, valores = cantidad)
      C) En ancho con una columna tipo 'Estructuras' con códigos separados por coma (fallback básico)

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
    c_punto = _find_col("Punto", "Puntos", "Nodo", "Nodos", "Poste", "Estructura Punto")

    # Detectar si ya viene largo
    c_cod = _find_col("codigodeestructura", "codigoestructura", "codigo de estructura", "estructura", "codigo", "cod")
    c_cant = _find_col("cantidad", "cant", "qty", "cantidad (p)", "cantidad_p", "n")

    if c_punto and c_cod and c_cant:
        df_long = out[[c_punto, c_cod, c_cant]].copy()
        df_long = df_long.rename(columns={c_punto: "Punto", c_cod: "codigodeestructura", c_cant: "cantidad"})
        return _postprocesar_largo(df_long)

    # Si no hay Punto explícito, intenta usar la primera columna como Punto
    if not c_punto and len(out.columns) >= 1:
        c_punto = out.columns[0]

    # Caso C: columna "Estructuras" con texto (opcional)
    c_estructs = _find_col("Estructuras", "Estructura", "Códigos", "Codigos", "Codigos de estructura")
    if c_estructs and c_punto:
        tmp = out[[c_punto, c_estructs]].copy()
        tmp = tmp.rename(columns={c_punto: "Punto"})
        # explotar por coma
        tmp["codigodeestructura"] = tmp[c_estructs].astype(str).str.split(",")
        tmp = tmp.explode("codigodeestructura")
        tmp["cantidad"] = 1
        tmp = tmp[["Punto", "codigodeestructura", "cantidad"]]
        return _postprocesar_largo(tmp)

    # Caso B: ancho clásico (Punto + columnas de estructuras)
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
