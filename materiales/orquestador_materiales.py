# -*- coding: utf-8 -*-

from __future__ import annotations
from typing import Dict, Any

import pandas as pd

# =========================
# IMPORTS
# =========================

from materiales.calculos.materiales_estructuras import calcular_materiales_estructura
from materiales.calculos.materiales_puntos import calcular_materiales_por_punto

from materiales.validaciones.materiales_validacion import validar_estructuras

# 👇 NUEVO
from core.cables_materiales import materiales_desde_cables


# =========================================================
# ORQUESTADOR REAL
# =========================================================

def ejecutar_materiales(entrada: Dict[str, Any]) -> Dict[str, Any]:

    errores = []
    warnings = []

    archivo_materiales = entrada.get("archivo_materiales")
    estructuras_por_punto = entrada.get("estructuras_por_punto")
    tension = entrada.get("tension")

    df_cables = entrada.get("df_cables")  # 👈 NUEVO

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
    # CÁLCULO MATERIALES
    # =====================================================

    try:
        # PUNTOS
        df_puntos = calcular_materiales_por_punto(
            archivo_materiales,
            estructuras_por_punto,
            tension
        )

        # 👇 CABLES (NUEVO)
        df_cables_mat = materiales_desde_cables(df_cables)

    except Exception as e:
        return {
            "ok": False,
            "errores": [f"Error en cálculos: {e}"],
            "warnings": warnings,
        }

    # =====================================================
    # CONSOLIDACIÓN TOTAL
    # =====================================================
    try:
        dfs = []

        if df_puntos is not None and not df_puntos.empty:
            dfs.append(df_puntos[["Materiales", "Unidad", "Cantidad"]])

        if df_cables_mat is not None and not df_cables_mat.empty:
            dfs.append(df_cables_mat)

        if not dfs:
            df_total = pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])
        else:
            df_total = pd.concat(dfs, ignore_index=True)

            df_total = (
                df_total
                .groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"]
                .sum()
            )

    except Exception as e:
        return {
            "ok": False,
            "errores": [f"Error consolidando: {e}"],
            "warnings": warnings,
        }

    # =====================================================
    # RESULTADO
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
