# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional
import pandas as pd

from costos_precios.costos_materiales import (
    calcular_lista_materiales_con_costos,
    preparar_catalogo_costos
)

from costos_precios.costos_estructuras import (
    calcular_costos_por_estructura
)
from costos_precios.precio_estructura import calcular_precio_estructura
from costos_precios.costos_operativos import calcular_costos_operativos
from ayuda.debug import debug_guardar


# =====================================================
# CONTRATO
# =====================================================
@dataclass
class EntradaCostos:
    df_materiales: pd.DataFrame
    df_catalogo: pd.DataFrame

    # 🔥 NUEVO
    df_estructuras: Optional[pd.DataFrame] = None
    df_materiales_por_estructura: Optional[Dict[str, pd.DataFrame]] = None


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
            "catalogo": _preview_df(entrada.df_catalogo),
        }

        # =====================================================
        # 2. PREPARAR CATÁLOGO
        # =====================================================
        df_costos = preparar_catalogo_costos(entrada.df_catalogo)

        debug["catalogo_procesado"] = _preview_df(df_costos)

        if df_costos is None or df_costos.empty:
            raise ValueError("df_costos vacío después de preparar")

        # =====================================================
        # 3. COSTOS DE MATERIALES
        # =====================================================
        df_materiales_costos = calcular_lista_materiales_con_costos(
            df_materiales=entrada.df_materiales,
            df_catalogo_costos=df_costos
        )

        debug["tabla_materiales_costos"] = _preview_df(df_materiales_costos)

        # =====================================================
        # 4. COSTOS DE ESTRUCTURA (SI EXISTE INFO)
        # =====================================================
        df_costos_estructura = None

        if (
            entrada.df_estructuras is not None
            and entrada.df_materiales_por_estructura is not None
        ):

            try:
                df_costos_estructura = calcular_costos_por_estructura(
                    df_estructuras=entrada.df_estructuras,
                    df_materiales_por_estructura=entrada.df_materiales_por_estructura,
                    df_precios_materiales=df_costos
                )

                debug["tabla_costos_estructura"] = _preview_df(df_costos_estructura)

            except Exception as e:
                debug["costos_estructura_error"] = str(e)

        else:
            debug["costos_estructura_warning"] = "No se proporcionaron datos de estructuras"


        # =====================================================
# 4.1 PRECIO POR ESTRUCTURA (🔥 NUEVO)
# =====================================================
df_precios_estructura = None

try:
    if df_costos_estructura is not None and not df_costos_estructura.empty:

        filas_precio = []

        for _, row in df_costos_estructura.iterrows():

            estructura = row["codigodeestructura"]
            costo_materiales = float(row["Costo Unitario"])

            # 🔥 COSTO OPERATIVO UNITARIO
            res_op = calcular_costos_operativos(
                costo_cuadrilla_dia=8000,     # ← AJUSTABLE
                fraccion_jornada=1/16,        # ← AJUSTABLE
                costo_equipos=50,
                costo_logistica=30,
            )

            # 🔥 PRECIO FINAL
            res_precio = calcular_precio_estructura(
                estructura=estructura,
                costo_materiales=costo_materiales,
                costo_operativo=res_op.operativo_total,
                porcentaje_utilidad=0.25,     # ← AJUSTABLE
            )

            filas_precio.append({
                "Estructura": estructura,
                "Cantidad": row["Cantidad"],
                "Costo Unitario": costo_materiales,
                "Costo Operativo": res_op.operativo_total,
                "Precio Unitario": res_precio.precio_unitario,
                "Precio Total": res_precio.precio_unitario * row["Cantidad"],
            })

        df_precios_estructura = pd.DataFrame(filas_precio)

        debug["tabla_precios_estructura"] = _preview_df(df_precios_estructura)

except Exception as e:
    debug["precio_estructura_error"] = str(e)


        
        # =====================================================
        # 5. MÉTRICAS
        # =====================================================
        total_materiales = float(df_materiales_costos["Costo Total"].sum())

        total_estructura = 0.0
        if df_costos_estructura is not None:
            total_estructura = float(df_costos_estructura["Costo Total"].sum())

        debug["metricas"] = {
            "total_materiales": total_materiales,
            "total_estructura": total_estructura,
            "total_global": total_materiales + total_estructura
        }

        # =====================================================
        # 6. DEBUG GLOBAL
        # =====================================================
        debug_guardar("ORQUESTADOR_COSTOS", debug)

        return {
            "ok": True,
            "df_materiales_costos": df_materiales_costos,
            "df_costos_estructura": df_costos_estructura,
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
            "df_costos_estructura": None,
            "df_precios_estructura": None,
            "debug": debug
        }
