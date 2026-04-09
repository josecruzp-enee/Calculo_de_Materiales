# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, Any, Union
from pathlib import Path

from entradas.base_datos import obtener_catalogo_materiales
from ayuda.debug import debug_guardar


# =========================================================
# NORMALIZACIÓN TEXTO
# =========================================================
def _norm_txt(s: object) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""

    t = str(s).upper()

    t = "".join(
        c for c in unicodedata.normalize("NFD", t)
        if unicodedata.category(c) != "Mn"
    )

    for p in ["DE", "DEL", "LA", "EL", "ANSI", "TIPO", "CLASE",
              "CARRETE", "ESPIGA", "SUSPENSION"]:
        t = t.replace(p, "")

    t = t.replace("-", " ")
    t = "".join(c if c.isalnum() else " " for c in t)
    t = " ".join(t.split())

    return t


# =========================================================
# CONTRATO (CORREGIDO)
# =========================================================
@dataclass
class EntradaCostos:
    df_resumen: pd.DataFrame
    df_estructuras_por_punto: pd.DataFrame
    df_materiales_por_estructura: Dict[str, pd.DataFrame] = field(default_factory=dict)
    fuente_precios: Union[pd.DataFrame, str, Path] = None


# =========================================================
# MOTOR DE COSTOS
# =========================================================
def calcular_costos_desde_resumen(df_resumen, df_costos):

    if df_resumen is None or df_resumen.empty:
        raise ValueError("df_resumen vacío")

    if df_costos is None or df_costos.empty:
        raise ValueError("df_costos vacío")

    df = df_resumen.copy()

    if "Unidad" not in df.columns:
        df["Unidad"] = ""

    df["Materiales_norm"] = df["Materiales"].astype(str).map(_norm_txt)
    df["Unidad_norm"] = df["Unidad"].astype(str).map(_norm_txt)

    df = df.merge(df_costos, on=["Materiales_norm", "Unidad_norm"], how="left")

    if df["Costo Unitario"].isna().any():
        raise ValueError("Hay materiales sin costo")

    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)
    df["Costo Total"] = df["Cantidad"] * df["Costo Unitario"]

    return df[[
        "Materiales", "Unidad", "Cantidad",
        "Costo Unitario", "Costo Total"
    ]].reset_index(drop=True)


# =========================================================
# BUILDER CORREGIDO
# =========================================================
def construir_entrada_costos(data, df_resumen, df_estructuras_por_punto):

    catalogo = obtener_catalogo_materiales(data)

    df_costos = preparar_df_costos_unitarios(catalogo)

    from costos_precios.orquestador_costos import EntradaCostos

    return EntradaCostos(
        df_resumen=df_resumen,
        df_estructuras_por_punto=df_estructuras_por_punto,
        df_materiales_por_estructura=data.get(
            "df_materiales_por_estructura", {}
        ),
        fuente_precios=df_costos,
    )


# =========================================================
# COSTOS UNITARIOS (SIMPLIFICADO SIN ERROR)
# =========================================================
def preparar_df_costos_unitarios(df_catalogo):

    if df_catalogo is None or df_catalogo.empty:
        raise ValueError("Catálogo vacío")

    df = df_catalogo.copy()

    df["Materiales_norm"] = df["Materiales"].astype(str).map(_norm_txt)
    df["Unidad_norm"] = df["Unidad"].astype(str).map(_norm_txt)

    df["Costo Unitario"] = pd.to_numeric(
        df.get("Costo Unitario", df.get("Costo", 0)),
        errors="coerce"
    )

    df = df.dropna(subset=["Costo Unitario"])
    df = df[df["Costo Unitario"] > 0]

    df = df.drop_duplicates(
        subset=["Materiales_norm", "Unidad_norm"]
    )

    return df[["Materiales_norm", "Unidad_norm", "Costo Unitario"]]
