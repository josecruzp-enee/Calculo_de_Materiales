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
# HELPERS DEBUG
# =====================================================
def _preview_df(df: pd.DataFrame, n=5):
    if df is None:
        return None
    return {
        "shape": df.shape,
        "columns": list(df.columns),
        "head": df.head(n).to_dict(orient="records")
    }


# =====================================================
# ORQUESTADOR
# =====================================================
def ejecutar_costos(entrada: EntradaCostos) -> Dict[str, Any]:

    debug: Dict[str, Any] = {}

    try:
        # =====================================================
        # 1. VALIDACIÓN
        # =====================================================
        if not isinstance(entrada.df_materiales, pd.DataFrame):
            raise TypeError("df_materiales inválido")

        if not isinstance(entrada.df_catalogo, pd.DataFrame):
            raise TypeError("df_catalogo inválido")

        debug["input"] = {
            "materiales": _preview_df(entrada.df_materiales),
            "catalogo": _preview_df(entrada.df_catalogo)
        }

        # =====================================================
        # 2. PREPARAR CATÁLOGO
        # =====================================================
        df_costos = preparar_catalogo_costos(entrada.df_catalogo)

        debug["catalogo_procesado"] = _preview_df(df_costos)

        if df_costos is None or df_costos.empty:
            raise ValueError("df_costos vacío después de preparar")

        # =====================================================
        # 3. CALCULAR COSTOS
        # =====================================================
        df_resultado = calcular_lista_materiales_con_costos(
            df_materiales=entrada.df_materiales,
            df_catalogo_costos=df_costos
        )

        debug["resultado_df"] = _preview_df(df_resultado)

        if df_resultado is None or df_resultado.empty:
            debug["warning"] = "Resultado vacío"

        # =====================================================
        # 4. MÉTRICAS
        # =====================================================
        costo_total = 0.0

        if "Costo Total" in df_resultado.columns:
            costo_total = float(df_resultado["Costo Total"].fillna(0).sum())
        else:
            debug["error_columna"] = "No existe 'Costo Total'"

        debug["metricas"] = {
            "filas": len(df_resultado),
            "costo_total": costo_total
        }

        # =====================================================
        # 5. DEBUG GLOBAL
        # =====================================================
        debug_guardar("ORQUESTADOR_COSTOS", debug)

        return {
            "ok": True,
            "df_materiales_costos": df_resultado,
            "debug": debug
        }

    except Exception as e:

        debug["exception"] = {
            "error": str(e)
        }

        debug_guardar("ORQUESTADOR_COSTOS_ERROR", debug)

        return {
            "ok": False,
            "errores": [str(e)],
            "df_materiales_costos": None,
            "debug": debug
        }
