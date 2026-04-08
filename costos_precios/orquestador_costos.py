# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Any

# =====================================================
# COSTOS BASE
# =====================================================
from costos_precios.costos_materiales import calcular_costos_desde_resumen
from costos_precios.costos_por_punto import calcular_costos_por_punto
from costos_precios.costos_estructuras import calcular_costos_por_estructura


def ejecutar_costos(data: Dict[str, Any]) -> Dict[str, Any]:

    if not isinstance(data, dict):
        raise TypeError("data debe ser dict")

    # =====================================================
    # INPUTS
    # =====================================================
    df_resumen = data.get("df_resumen")
    df_ep = data.get("df_estructuras_por_punto")
    df_estructuras = data.get("df_estructuras")

    if df_resumen is None:
        raise ValueError("Falta df_resumen")

    if df_ep is None:
        raise ValueError("Falta df_estructuras_por_punto")

    if df_estructuras is None:
        raise ValueError("Falta df_estructuras")

    # =====================================================
    # 1. COSTOS MATERIALES
    # =====================================================
    fuente_precios = (
        data.get("df_precios_materiales")
        or data.get("ruta_materiales")
    )

    df_costos_materiales = calcular_costos_desde_resumen(
        df_resumen,
        fuente_precios
    )

    # =====================================================
    # 2. COSTOS ESTRUCTURAS (🔥 AHORA AQUÍ)
    # =====================================================
    df_costos_estructuras = calcular_costos_por_estructura(
        hojas_base=data.get("hojas_base"),
        conteo=None,  # ⚠️ aquí luego optimizamos
        tension_ll=data.get("tension"),
        calibre_mt=data.get("calibre_mt"),
        tabla_conectores_mt=data.get("tabla_conectores_mt"),

        costo_cuadrilla_dia=data.get("costo_cuadrilla_dia", 1250),
        fraccion_jornada=data.get("fraccion_jornada", 1/16),
        costo_equipos=data.get("costo_equipos", 0),
        costo_logistica=data.get("costo_logistica", 0),
        margen_utilidad=data.get("margen_utilidad", 0.15),
    )

    # =====================================================
    # 3. COSTOS POR PUNTO
    # =====================================================
    df_detalle, df_resumen_costos, df_resumen_precios = calcular_costos_por_punto(
        df_ep,
        df_costos_estructuras
    )

    # =====================================================
    # OUTPUT
    # =====================================================
    return {
        "df_costos_materiales": df_costos_materiales,
        "df_costos_estructuras": df_costos_estructuras,
        "df_costos_por_punto": df_detalle,
        "df_resumen_costos_punto": df_resumen_costos,
        "df_resumen_precios_punto": df_resumen_precios,
    }
