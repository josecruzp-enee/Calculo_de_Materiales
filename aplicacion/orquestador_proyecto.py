# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional, Dict, Any
import pandas as pd

from interfaz.contratos import SalidaInterfaz, SalidaEntradas
from entradas.orquestador_entradas import ejecutar_entradas


# =========================================================
# HELPERS
# =========================================================
def _fail(msg: str) -> Dict[str, Any]:
    return {
        "ok": False,
        "errores": [msg],
        "warnings": [],
        "debug": {}
    }


def _extraer_tension(datos: Dict[str, Any]) -> float:
    t = datos.get("tension") or datos.get("nivel_de_tension")
    if t is None:
        raise ValueError("Tensión no definida")
    t = float(t)
    if t <= 0:
        raise ValueError("Tensión inválida")
    return t


# =========================================================
# ORQUESTADOR PRINCIPAL
# =========================================================
def ejecutar_proyecto(salida_interfaz: SalidaInterfaz) -> Dict[str, Any]:

    debug_global = {}

    try:

        debug_global["ETAPA"] = "INICIO"

        # =====================================================
        # 1. ENTRADAS
        # =====================================================
        salida_entradas = ejecutar_entradas(salida_interfaz)

        if not salida_entradas or not getattr(salida_entradas, "ok", False):
            return _fail("Error en orquestador de entradas")

        debug_global["ENTRADAS_OK"] = True

        # =====================================================
        # 2. DF ESTRUCTURAS
        # =====================================================
        df_estructuras = salida_entradas.df_estructuras

        debug_global["DF_ESTRUCTURAS"] = None if df_estructuras is None else df_estructuras.shape

        # =====================================================
        # 3. TENSIÓN
        # =====================================================
        datos_proyecto = salida_entradas.datos_proyecto or {}
        tension = _extraer_tension(datos_proyecto)

        debug_global["TENSION"] = tension

        # =====================================================
        # 4. SALIDA FINAL (ESTABLE)
        # =====================================================
        return {
            "ok": True,
            "errores": [],
            "warnings": [],
            "tension": tension,
            "df_estructuras": df_estructuras,
            "base_datos": salida_entradas.base_datos,
            "datos_proyecto": datos_proyecto,
            "df_cables": salida_entradas.df_cables,
            "debug": debug_global
        }

    except Exception as e:
        return {
            "ok": False,
            "errores": [str(e)],
            "warnings": [],
            "debug": debug_global
        }
