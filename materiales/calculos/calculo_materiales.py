# -*- coding: utf-8 -*-
from __future__ import annotations
import pandas as pd

from materiales.calculos.materiales_puntos import calcular_materiales_por_punto
from ayuda.debug import debug_guardar
from materiales.cables.cables_materiales import materiales_desde_cables
COLUMNAS_STD = ["Materiales", "Unidad", "Cantidad"]


# =========================================================
# VALIDADORES
# =========================================================
def _validar_df_estructuras(df: pd.DataFrame):

    if df is None:
        raise ValueError("df_estructuras es None")

    if not isinstance(df, pd.DataFrame):
        raise TypeError("df_estructuras debe ser DataFrame")

    if df.empty:
        raise ValueError("df_estructuras está vacío")

    if "Estructura" not in df.columns:
        raise ValueError(
            f"df_estructuras debe contener columna 'Estructura'. "
            f"Columnas actuales: {list(df.columns)}"
        )


def _validar_hojas_base(hojas_base):

    if hojas_base is None:
        raise ValueError("hojas_base es None")

    if not isinstance(hojas_base, dict):
        raise TypeError("hojas_base debe ser dict[str, DataFrame]")

    if not hojas_base:
        raise ValueError("hojas_base está vacío")


def _validar_df_salida(df: pd.DataFrame):

    if df is None or df.empty:
        raise ValueError("Resultado de materiales vacío")

    if not set(COLUMNAS_STD).issubset(df.columns):
        raise ValueError(
            f"Columnas inválidas. Esperadas: {COLUMNAS_STD}, "
            f"recibidas: {list(df.columns)}"
        )

    if df["Materiales"].isna().any():
        raise ValueError("Materiales contiene nulos")

    if df["Unidad"].isna().any():
        raise ValueError("Unidad contiene nulos")

    cantidades = pd.to_numeric(df["Cantidad"], errors="coerce")

    if cantidades.isna().any():
        raise ValueError("Cantidad inválida")

    if (cantidades < 0).any():
        raise ValueError("Cantidad negativa")


# =========================================================
# NORMALIZACIÓN
# =========================================================
def _normalizar_estructuras(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()

    df["Estructura"] = (
        df["Estructura"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    return df


def _normalizar_df_materiales(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()

    df["Materiales"] = df["Materiales"].astype(str).str.strip()
    df["Unidad"] = df["Unidad"].astype(str).str.strip()
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0.0)

    return df


# =========================================================
# VALIDAR MATCH CONTRA BASE
# =========================================================
def _validar_match_estructuras(df_estructuras, hojas_base):

    estructuras = df_estructuras["Estructura"].unique()

    debug_guardar("CALCULO::estructuras_unicas", list(estructuras)[:50])

    faltantes = [e for e in estructuras if e not in hojas_base]

    if faltantes:
        raise ValueError(
            f"Estructuras no encontradas ({len(faltantes)}): {faltantes[:10]}"
        )


# =========================================================
# CONSOLIDACIÓN GLOBAL
# =========================================================
def _consolidar(df: pd.DataFrame) -> pd.DataFrame:

    return (
        df
        .groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"]
        .sum()
        .sort_values(["Materiales", "Unidad"])
        .reset_index(drop=True)
    )


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================
# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================
def calcular_materiales_proyecto(
    *,
    hojas_base,
    df_estructuras,
    tension,
    calibre_mt=None,
    tabla_conectores_mt=None,
    df_cables=None,  # 🔥 NUEVO
) -> dict:

    from materiales.cables.cables_materiales import materiales_desde_cables

    # -----------------------------
    # DEBUG INPUT
    # -----------------------------
    debug_guardar("CALCULO::input", {
        "filas_estructuras": None if df_estructuras is None else len(df_estructuras),
        "tension": tension,
        "tiene_cables": isinstance(df_cables, pd.DataFrame)
    })

    # -----------------------------
    # VALIDACIONES BASE
    # -----------------------------
    _validar_df_estructuras(df_estructuras)
    _validar_hojas_base(hojas_base)

    if tension is None or float(tension) <= 0:
        raise ValueError("tension no válida")

    # -----------------------------
    # NORMALIZAR INPUT
    # -----------------------------
    df_estructuras = _normalizar_estructuras(df_estructuras)

    # -----------------------------
    # VALIDAR MATCH
    # -----------------------------
    _validar_match_estructuras(df_estructuras, hojas_base)

    # -----------------------------
    # CÁLCULO DETALLE (ESTRUCTURAS)
    # -----------------------------
    try:
        df_detalle = calcular_materiales_por_punto(
            hojas_base=hojas_base,
            df_estructuras=df_estructuras,
            tension=tension,
            calibre_mt=calibre_mt,
            tabla_conectores_mt=tabla_conectores_mt
        )
    except Exception as e:
        raise RuntimeError(f"Error en materiales_por_punto: {e}")

    if not isinstance(df_detalle, pd.DataFrame):
        raise TypeError("calcular_materiales_por_punto no devolvió DataFrame")

    df_detalle = _normalizar_df_materiales(df_detalle)
    _validar_df_salida(df_detalle)

    # =====================================================
    # 🔥 INTEGRACIÓN DE CABLES (AQUÍ ESTÁ LA MAGIA)
    # =====================================================
    df_cables_mat = materiales_desde_cables(df_cables)

    if isinstance(df_cables_mat, pd.DataFrame) and not df_cables_mat.empty:

        df_cables_mat = _normalizar_df_materiales(df_cables_mat)

        df_detalle = pd.concat(
            [df_detalle, df_cables_mat],
            ignore_index=True
        )

        debug_guardar("CALCULO::cables_integrados", {
            "filas_cables": len(df_cables_mat)
        })

    # -----------------------------
    # CONSOLIDADO GLOBAL
    # -----------------------------
    df_global = _consolidar(df_detalle)
    df_global = _normalizar_df_materiales(df_global)
    _validar_df_salida(df_global)

    # -----------------------------
    # DEBUG OUTPUT
    # -----------------------------
    debug_guardar("CALCULO::output", {
        "materiales_total": len(df_global),
        "detalle_total": len(df_detalle)
    })

    # -----------------------------
    # OUTPUT FINAL
    # -----------------------------
    return {
        "ok": True,
        "df_materiales": df_global,
        "df_materiales_por_punto": df_detalle
    }
