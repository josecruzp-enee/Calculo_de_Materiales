# -*- coding: utf-8 -*-
"""
Orquestador del dominio de materiales.

Flujo:
Entradas → Validación → Cálculo → Consolidación → Salida
"""

from __future__ import annotations
from typing import Dict, Any

import pandas as pd

# =========================
# IMPORTS DOMINIO
# =========================

# Entradas
from materiales.parser.estructuras import procesar_entrada_estructuras

# Validación
from materiales.validaciones.validar_estructuras import validar_estructuras

# Cálculos
from materiales.calculos.materiales_por_estructura import calcular_materiales_estructuras
from materiales.calculos.materiales_por_punto import calcular_materiales_puntos

# Consolidación
from materiales.consolidacion.consolidar_materiales import consolidar_materiales

# Salida
from materiales.salida.dataframe_materiales import construir_dataframe_materiales


# =========================================================
# ORQUESTADOR
# =========================================================

def ejecutar_materiales(entrada: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ejecuta todo el flujo del dominio de materiales.

    Parameters
    ----------
    entrada : dict
        Datos de entrada desde UI o archivo.

    Returns
    -------
    dict con:
        ok: bool
        errores: list
        warnings: list
        df_materiales: DataFrame final
        resumen: dict
    """

    errores = []
    warnings = []

    # =====================================================
    # 1. ENTRADAS
    # =====================================================
    try:
        estructuras = procesar_entrada_estructuras(entrada)
    except Exception as e:
        return {
            "ok": False,
            "errores": [f"Error procesando entrada: {e}"],
            "warnings": [],
        }

    # =====================================================
    # 2. VALIDACIÓN
    # =====================================================
    val = validar_estructuras(estructuras)

    if not val["ok"]:
        return {
            "ok": False,
            "errores": val["errores"],
            "warnings": val.get("warnings", []),
        }

    warnings.extend(val.get("warnings", []))

    # =====================================================
    # 3. CÁLCULOS
    # =====================================================
    try:
        mat_estructuras = calcular_materiales_estructuras(estructuras)
        mat_puntos = calcular_materiales_puntos(estructuras)
    except Exception as e:
        return {
            "ok": False,
            "errores": [f"Error en cálculos: {e}"],
            "warnings": warnings,
        }

    # =====================================================
    # 4. CONSOLIDACIÓN
    # =====================================================
    try:
        materiales_total = consolidar_materiales(
            mat_estructuras,
            mat_puntos
        )
    except Exception as e:
        return {
            "ok": False,
            "errores": [f"Error consolidando materiales: {e}"],
            "warnings": warnings,
        }

    # =====================================================
    # 5. SALIDA
    # =====================================================
    try:
        df_materiales = construir_dataframe_materiales(materiales_total)
    except Exception as e:
        return {
            "ok": False,
            "errores": [f"Error generando salida: {e}"],
            "warnings": warnings,
        }

    # =====================================================
    # RESULTADO FINAL
    # =====================================================
    return {
        "ok": True,
        "errores": [],
        "warnings": warnings,
        "df_materiales": df_materiales,
        "resumen": {
            "total_items": len(df_materiales),
        }
    }
