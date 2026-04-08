# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Any

from costos_precios.costos_materiales import calcular_costos_desde_resumen
from costos_precios.costos_por_punto import calcular_costos_por_punto


def ejecutar_costos(data: Dict[str, Any]) -> Dict[str, Any]:

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

    # ----------------------------------------
    # COSTOS MATERIALES
    # ----------------------------------------
    fuente_precios = data.get("df_precios_materiales") or data.get("archivo_precios_materiales")

    df_costos_materiales = calcular_costos_desde_resumen(
        df_resumen,
        fuente_precios
    )

    # ----------------------------------------
    # COSTOS POR PUNTO
    # ----------------------------------------
    df_detalle, df_resumen_costos, df_resumen_precios = calcular_costos_por_punto(
        df_ep,
        df_costos_estructuras
    )

    return {
        "df_costos_materiales": df_costos_materiales,
        "df_costos_estructuras": df_costos_estructuras,  # 🔥 CLAVE
        "df_costos_por_punto": df_detalle,
        "df_resumen_costos_punto": df_resumen_costos,
        "df_resumen_precios_punto": df_resumen_precios,
    }
