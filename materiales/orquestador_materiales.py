# -*- coding: utf-8 -*-

from __future__ import annotations

import pandas as pd

# =========================
# MODELOS
# =========================
from materiales.modelos.entrada import EntradaMateriales
from materiales.modelos.salida import ResultadoMateriales

# =========================
# DOMINIO
# =========================
from materiales.calculos.materiales_puntos import calcular_materiales_por_punto
from materiales.validaciones.materiales_validacion import validar_estructuras

# ⚠️ TEMPORAL (luego migrar a materiales/)
from core.cables_materiales import materiales_desde_cables


# =========================================================
# CONFIG
# =========================================================

COLUMNAS_STD = ["Materiales", "Unidad", "Cantidad"]


# =========================================================
# HELPERS
# =========================================================

def _normalizar_df(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=COLUMNAS_STD)

    df = df.copy()

    for col in COLUMNAS_STD:
        if col not in df.columns:
            if col == "Cantidad":
                df[col] = 0.0
            else:
                df[col] = ""

    return df[COLUMNAS_STD]


def _df_a_por_punto(df: pd.DataFrame):

    """
    Convierte DataFrame de estructuras a:
    {punto: [estructuras]}
    """

    resultado = {}

    for _, row in df.iterrows():

        punto = str(row.get("Punto", "")).strip()
        estructura = str(row.get("codigodeestructura", "")).strip().upper()

        if not punto or not estructura:
            continue

        if punto not in resultado:
            resultado[punto] = []

        resultado[punto].append(estructura)

    return resultado


# =========================================================
# ORQUESTADOR
# =========================================================

def ejecutar_materiales(entrada: EntradaMateriales) -> ResultadoMateriales:

    warnings = []

    # =====================================================
    # INPUTS TIPADOS
    # =====================================================
    estructuras_df = entrada.estructuras_df
    tension = entrada.tension
    df_cables = entrada.df_cables

    # =====================================================
    # TRANSFORMACIÓN
    # =====================================================
    estructuras_por_punto = _df_a_por_punto(estructuras_df)

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    val = validar_estructuras(estructuras_por_punto)

    if not val.get("ok", True):
        return ResultadoMateriales(
            ok=False,
            df_materiales=pd.DataFrame(),
            errores=val.get("errores", []),
            warnings=val.get("warnings", [])
        )

    warnings.extend(val.get("warnings", []))

    # =====================================================
    # CÁLCULOS
    # =====================================================
    try:
        df_puntos = calcular_materiales_por_punto(
            None,  # si luego usas base de datos, aquí la pasas
            estructuras_por_punto,
            tension
        )

        df_cables_mat = materiales_desde_cables(df_cables)

    except Exception as e:
        return ResultadoMateriales(
            ok=False,
            df_materiales=pd.DataFrame(),
            errores=[f"Error en cálculos: {e}"],
            warnings=warnings
        )

    # =====================================================
    # NORMALIZACIÓN
    # =====================================================
    df_puntos = _normalizar_df(df_puntos)
    df_cables_mat = _normalizar_df(df_cables_mat)

    # =====================================================
    # CONSOLIDACIÓN
    # =====================================================
    try:
        df_total = pd.concat(
            [df_puntos, df_cables_mat],
            ignore_index=True
        )

        if not df_total.empty:
            df_total = (
                df_total
                .groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"]
                .sum()
                .sort_values("Materiales")
            )

    except Exception as e:
        return ResultadoMateriales(
            ok=False,
            df_materiales=pd.DataFrame(),
            errores=[f"Error consolidando: {e}"],
            warnings=warnings
        )

    # =====================================================
    # RESULTADO FINAL
    # =====================================================
    return ResultadoMateriales(
        ok=True,
        df_materiales=df_total,
        errores=[],
        warnings=warnings
    )
