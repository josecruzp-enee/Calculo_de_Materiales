# -*- coding: utf-8 -*-

from __future__ import annotations
from typing import Dict, Any
import pandas as pd

# =========================
# IMPORTS
# =========================

from entradas.base_datos import cargar_base_datos

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


# =========================================================
# ORQUESTADOR
# =========================================================

def ejecutar_materiales(entrada: Dict[str, Any]) -> Dict[str, Any]:

    errores = []
    warnings = []

    # =====================================================
    # INPUTS USUARIO
    # =====================================================
    estructuras_por_punto = entrada.get("estructuras_por_punto")
    tension = entrada.get("tension")
    df_cables = entrada.get("df_cables")

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    val = validar_estructuras(estructuras_por_punto)

    if not val.get("ok", True):
        return {
            "ok": False,
            "errores": val.get("errores", []),
            "warnings": val.get("warnings", []),
        }

    warnings.extend(val.get("warnings", []))

    # =====================================================
    # BASE DE DATOS (🔥 CENTRALIZADO)
    # =====================================================
    try:
        hojas_base = cargar_base_datos()
    except Exception as e:
        return {
            "ok": False,
            "errores": [f"Error cargando base de datos: {e}"],
            "warnings": warnings,
        }

    # =====================================================
    # CÁLCULOS
    # =====================================================
    try:
        # 🔹 MATERIALES POR ESTRUCTURA
        df_puntos = calcular_materiales_por_punto(
            hojas_base,
            estructuras_por_punto,
            tension
        )

        # 🔹 CABLES
        df_cables_mat = materiales_desde_cables(df_cables)

    except Exception as e:
        return {
            "ok": False,
            "errores": [f"Error en cálculos: {e}"],
            "warnings": warnings,
        }

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
        return {
            "ok": False,
            "errores": [f"Error consolidando: {e}"],
            "warnings": warnings,
        }

    # =====================================================
    # RESULTADO FINAL
    # =====================================================
    return {
        "ok": True,
        "errores": [],
        "warnings": warnings,
        "df_materiales": df_total,
        "resumen": {
            "total_items": len(df_total),
        }
    }
