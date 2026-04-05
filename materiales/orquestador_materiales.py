# -*- coding: utf-8 -*-
"""
Orquestador del dominio de materiales (adaptado al proyecto actual)
"""

from __future__ import annotations
from typing import Dict, Any

import pandas as pd

# =========================
# IMPORTS REALES
# =========================

# Validación
from materiales.validaciones.materiales_validacion import validar_estructuras

# Cálculos
from materiales.calculos.materiales_estructuras import calcular_materiales_estructuras
from materiales.calculos.materiales_puntos import calcular_materiales_puntos


# =========================================================
# ORQUESTADOR
# =========================================================

def ejecutar_materiales(entrada: Dict[str, Any]) -> Dict[str, Any]:

    errores = []
    warnings = []

    # =====================================================
    # 1. ENTRADA (YA VIENE PROCESADA DESDE UI)
    # =====================================================
    estructuras = entrada  # 👈 clave en tu proyecto actual

    # =====================================================
    # 2. VALIDACIÓN
    # =====================================================
    val = validar_estructuras(estructuras)

    if not val.get("ok", True):
        return {
            "ok": False,
            "errores": val.get("errores", []),
            "warnings": val.get("warnings", []),
        }

    warnings.extend(val.get("warnings", []))

    # =====================================================
    # 3. CÁLCULOS
    # =====================================================
    try:
        df_estructuras = calcular_materiales_estructuras(estructuras)
        df_puntos = calcular_materiales_puntos(estructuras)

    except Exception as e:
        return {
            "ok": False,
            "errores": [f"Error en cálculos: {e}"],
            "warnings": warnings,
        }

    # =====================================================
    # 4. CONSOLIDACIÓN (REALISTA)
    # =====================================================
    try:
        df_total = pd.concat([df_estructuras, df_puntos], ignore_index=True)

        # Agrupar si aplica
        if "Cantidad" in df_total.columns:
            df_total = (
                df_total
                .groupby(list(df_total.columns.difference(["Cantidad"])))
                ["Cantidad"]
                .sum()
                .reset_index()
            )

    except Exception as e:
        return {
            "ok": False,
            "errores": [f"Error consolidando: {e}"],
            "warnings": warnings,
        }

    # =====================================================
    # 5. SALIDA
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
