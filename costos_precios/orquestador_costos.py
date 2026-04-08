# -*- coding: utf-8 -*-
"""
costos_precios/orquestador_costos.py

Orquestador del dominio de costos.

Responsabilidad:
- Coordinar cálculos de costos
- No contiene lógica matemática
- No lee Excel directamente (excepto vía servicios)

Flujo:
materiales → estructuras → costos → consolidación
"""

from __future__ import annotations

from typing import Dict, Any

# servicios dominio
from costos_precios.costos_materiales import calcular_costos_desde_resumen
from costos_precios.costos_por_punto import calcular_costos_por_punto


# =========================================================
# ORQUESTADOR
# =========================================================
def ejecutar_costos(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ejecuta todos los cálculos de costos.

    INPUT:
        data:
            df_resumen
            df_estructuras_por_punto
            df_costos_estructuras (opcional)
            archivo_precios_materiales (opcional)

    OUTPUT:
        dict con DataFrames de costos
    """

    # -----------------------------------------------------
    # VALIDACIÓN
    # -----------------------------------------------------
    if not isinstance(data, dict):
        raise TypeError("data debe ser dict")

    df_resumen = data.get("df_resumen")
    df_ep = data.get("df_estructuras_por_punto")

    if df_resumen is None:
        raise ValueError("Falta df_resumen")

    if df_ep is None:
        raise ValueError("Falta df_estructuras_por_punto")

    # -----------------------------------------------------
    # COSTOS MATERIALES
    # -----------------------------------------------------
    precios_materiales = data.get("df_precios_materiales")
    archivo_precios = data.get("archivo_precios_materiales")

    if precios_materiales is None and archivo_precios is None:
        raise ValueError("Debe proporcionar precios de materiales")

    fuente_precios = precios_materiales or archivo_precios

    df_costos_materiales = calcular_costos_desde_resumen(
        df_resumen,
        fuente_precios
    )

    # -----------------------------------------------------
    # COSTOS POR PUNTO
    # -----------------------------------------------------
    df_costos_estructuras = data.get("df_costos_estructuras")

    if df_costos_estructuras is None:
        raise ValueError("Falta df_costos_estructuras para calcular costos por punto")

    df_costos_por_punto, df_resumen_costos_punto = calcular_costos_por_punto(
        df_ep,
        df_costos_estructuras
    )

    # -----------------------------------------------------
    # OUTPUT
    # -----------------------------------------------------
    return {
        "df_costos_materiales": df_costos_materiales,
        "df_costos_por_punto": df_costos_por_punto,
        "df_resumen_costos_punto": df_resumen_costos_punto,
    }
