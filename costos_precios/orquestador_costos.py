# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any
import pandas as pd

from costos_precios.costos_materiales import (
    calcular_lista_materiales_con_costos,
    preparar_catalogo_costos
)

from ayuda.debug import debug_guardar


# =====================================================
# CONTRATO
# =====================================================
@dataclass
class EntradaCostos:
    df_materiales: pd.DataFrame
    df_catalogo: pd.DataFrame


# =====================================================
# ORQUESTADOR
# =====================================================
def ejecutar_costos(entrada: EntradaCostos) -> Dict[str, Any]:

    debug = {}

    # VALIDACIÓN
    if not isinstance(entrada.df_materiales, pd.DataFrame):
        raise TypeError("df_materiales inválido")

    if not isinstance(entrada.df_catalogo, pd.DataFrame):
        raise TypeError("df_catalogo inválido")

    debug["input"] = {
        "materiales_filas": len(entrada.df_materiales),
        "catalogo_filas": len(entrada.df_catalogo)
    }

    # PREPARAR CATÁLOGO
    df_costos = preparar_catalogo_costos(entrada.df_catalogo)

    # CALCULAR COSTOS
    df_resultado = calcular_lista_materiales_con_costos(
        df_materiales=entrada.df_materiales,
        df_catalogo_costos=df_costos
    )

    debug["resultado"] = {
        "filas": len(df_resultado),
        "costo_total": float(df_resultado["Costo Total"].sum())
    }

    debug_guardar("ORQUESTADOR_COSTOS", debug)

    return {
        "ok": True,
        "df_materiales_costos": df_resultado,
        "debug": debug
    }
