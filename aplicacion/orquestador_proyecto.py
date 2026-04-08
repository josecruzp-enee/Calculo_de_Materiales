# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Any

from materiales.orquestador_materiales import ejecutar_materiales
from costos_precios.orquestador_costos import ejecutar_costos
from costos_precios.costos_estructuras import calcular_costos_por_estructura


def ejecutar_proyecto(data: Dict[str, Any]) -> Dict[str, Any]:

    if not isinstance(data, dict):
        raise TypeError("data debe ser dict")

    # =====================================================
    # 1. MATERIALES
    # =====================================================
    salida_materiales = ejecutar_materiales(data)

    df_materiales = salida_materiales["df_materiales"]
    df_por_punto = salida_materiales["df_materiales_por_punto"]
    conteo = salida_materiales["conteo_estructuras"]

    base = data.get("hojas_base")

    # =====================================================
    # 2. COSTOS POR ESTRUCTURA
    # =====================================================
    df_costos_estructuras = calcular_costos_por_estructura(
        hojas_base=base,
        conteo=conteo,
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
    # 3. COSTOS GENERALES
    # =====================================================
    costos = ejecutar_costos({
        "df_resumen": df_materiales,
        "df_estructuras_por_punto": data.get("df_estructuras"),
        "df_costos_estructuras": df_costos_estructuras,
        "archivo_precios_materiales": data.get("archivo_materiales"),
    })

    # =====================================================
    # 4. OUTPUT FINAL
    # =====================================================
    return {
        "materiales": salida_materiales,
        "costos": costos,
        "df_costos_estructuras": df_costos_estructuras,
    }
