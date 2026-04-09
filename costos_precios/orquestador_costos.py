# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Any

# =====================================================
# COSTOS BASE
# =====================================================
from costos_precios.costos_materiales import calcular_costos_desde_resumen
from costos_precios.costos_por_punto import calcular_costos_por_punto


def ejecutar_costos(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Orquestador de dominio para costos.
    """

    # =====================================================
    # VALIDACIÓN INPUT
    # =====================================================
    if not isinstance(data, dict):
        raise TypeError("data debe ser dict")

    df_resumen = data.get("df_resumen")
    df_ep = data.get("df_estructuras_por_punto")
    df_costos_estructuras = data.get("df_costos_estructuras")

    if df_resumen is None:
        raise ValueError("Falta df_resumen")

    if df_ep is None:
        raise ValueError("Falta df_estructuras_por_punto")

    if df_costos_estructuras is None:
        raise ValueError("Falta df_costos_estructuras")

    # =====================================================
    # 1. FUENTE DE PRECIOS (FIX REAL)
    # =====================================================
    fuente_precios = data.get("df_precios_materiales")

    if fuente_precios is None:
        fuente_precios = data.get("archivo_precios_materiales")

    if fuente_precios is None:
        raise ValueError(
            "Debe proporcionar df_precios_materiales o archivo_precios_materiales"
        )

    # =====================================================
    # 2. COSTOS DE MATERIALES
    # =====================================================
    df_costos_materiales = calcular_costos_desde_resumen(
        df_resumen,
        fuente_precios
    )

    # =====================================================
    # 3. COSTOS POR PUNTO
    # =====================================================
    df_detalle, df_resumen_costos, df_resumen_precios = calcular_costos_por_punto(
        df_ep,
        df_costos_estructuras
    )

    # =====================================================
    # 4. CONSOLIDACIÓN
    # =====================================================
    resultados = {
        "df_costos_materiales": df_costos_materiales,
        "df_costos_estructuras": df_costos_estructuras,
        "df_costos_por_punto": df_detalle,
        "df_resumen_costos_punto": df_resumen_costos,
        "df_resumen_precios_punto": df_resumen_precios,
    }

    return resultados
