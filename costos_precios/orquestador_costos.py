# costos_precios/orquestador_costos.py

from __future__ import annotations
from typing import Dict, Any

# servicios dominio
from costos_precios.costos_materiales import calcular_costos_desde_resumen
from costos_precios.costos_por_punto import calcular_costos_por_punto


def ejecutar_costos(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ejecuta todos los cálculos de costos.

    Flujo:
    materiales → estructuras → costos → precios → consolidación
    """

    # -----------------------------------------------------
    # VALIDACIÓN
    # -----------------------------------------------------
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

    # -----------------------------------------------------
    # COSTOS MATERIALES
    # -----------------------------------------------------
    precios_materiales = data.get("df_precios_materiales")
    archivo_precios = data.get("archivo_precios_materiales")

    if precios_materiales is None and archivo_precios is None:
        raise ValueError("Debe proporcionar precios de materiales")

    fuente_precios = precios_materiales if precios_materiales is not None else archivo_precios

    df_costos_materiales = calcular_costos_desde_resumen(
        df_resumen,
        fuente_precios
    )

    # 🔹 total materiales (para reportes globales si quieres luego)
    total_materiales = float(
        df_costos_materiales["Costo"]
        .fillna(0)
        .sum()
    )

    # -----------------------------------------------------
    # COSTOS + PRECIOS POR PUNTO
    # -----------------------------------------------------
    df_detalle_punto, df_resumen_costos_punto, df_resumen_precios_punto = calcular_costos_por_punto(
        df_ep,
        df_costos_estructuras
    )

    # -----------------------------------------------------
    # CONSOLIDACIÓN GLOBAL
    # -----------------------------------------------------
    total_costo_proyecto = float(
        df_resumen_costos_punto["TOTAL_COSTO_PUNTO"]
        .sum()
    )

    total_precio_proyecto = float(
        df_resumen_precios_punto["TOTAL_PRECIO_PUNTO"]
        .sum()
    )

    utilidad_total = total_precio_proyecto - total_costo_proyecto

    # -----------------------------------------------------
    # OUTPUT
    # -----------------------------------------------------
    return {
        # 🔹 materiales
        "df_costos_materiales": df_costos_materiales,
        "total_materiales": round(total_materiales, 2),

        # 🔥 estructuras (CRÍTICO)
        "df_costos_estructuras": df_costos_estructuras,

        # 🔹 detalle por punto
        "df_costos_por_punto": df_detalle_punto,

        # 🔹 resúmenes
        "df_resumen_costos_punto": df_resumen_costos_punto,
        "df_resumen_precios_punto": df_resumen_precios_punto,

        # 🔹 global
        "total_costo_proyecto": round(total_costo_proyecto, 2),
        "total_precio_proyecto": round(total_precio_proyecto, 2),
        "utilidad_total": round(utilidad_total, 2),
    }
