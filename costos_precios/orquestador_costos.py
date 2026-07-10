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
from costos_precios.precio_estructura import _agregar_cable_a_precios
#from costos_precios.costos_operativos import calcular_costos_operativos
#from costos_precios.precio_estructura import calcular_precio_estructura
from costos_precios.mano_obra_por_punto import calcular_mano_obra_proyecto

from ayuda.debug import debug_guardar


# =====================================================
# CONTRATO
# =====================================================
@dataclass
class EntradaCostos:
    df_materiales: pd.DataFrame
    df_catalogo: pd.DataFrame

    df_estructuras: Optional[pd.DataFrame] = None
    df_materiales_por_estructura: Optional[Dict[str, pd.DataFrame]] = None

    ruta_datos_materiales: Optional[str] = None
    df_cables: Optional[pd.DataFrame] = None 
    contratista: str = "C1"

# =====================================================
# HELPERS
# =====================================================
def _preview_df(df: pd.DataFrame, n=5):
    if df is None:
        return None
    return {
        "shape": df.shape,
        "columns": list(df.columns),
        "head": df.head(n).to_dict(orient="records")
    }


def calcular_costos_cable(df_cables):
    total = 0

    for _, r in df_cables.iterrows():

        tipo = str(r.get("tipo", "")).strip().upper()

        try:
            longitud = float(r.get("longitud", 0))
        except:
            continue

        if tipo == "PRIMARIO":
            precio = 120
        elif tipo == "SECUNDARIO":
            precio = 80
        else:
            continue

        total += longitud * precio

    return total


# =====================================================
# ORQUESTADOR
# =====================================================
def ejecutar_costos(entrada: EntradaCostos) -> Dict[str, Any]:

    debug: Dict[str, Any] = {}

    try:

        debug["CABLES_EN_COSTOS"] = getattr(
            entrada,
            "_datos_proyecto",
            {}
        )

        # =====================================================
        # 1. VALIDACIÓN
        # =====================================================
        if not isinstance(entrada.df_materiales, pd.DataFrame):
            raise TypeError("df_materiales inválido")

        if not isinstance(entrada.df_catalogo, pd.DataFrame):
            raise TypeError("df_catalogo inválido")

        debug["input"] = {
            "materiales": _preview_df(
                entrada.df_materiales
            ),

            "catalogo": _preview_df(
                entrada.df_catalogo
            ),
        }

        # =====================================================
        # 2. CATÁLOGO
        # =====================================================
        df_costos = preparar_catalogo_costos(
            entrada.df_catalogo
        )

        if df_costos is None or df_costos.empty:
            raise ValueError("df_costos vacío")

        debug["df_costos"] = _preview_df(df_costos)

        # =====================================================
        # 3. COSTOS DE MATERIALES
        # =====================================================
        df_materiales_costos = (
            calcular_lista_materiales_con_costos(
                df_materiales=entrada.df_materiales,
                df_catalogo_costos=df_costos
            )
        )

        if (
            df_materiales_costos is None
            or not isinstance(df_materiales_costos, pd.DataFrame)
            or df_materiales_costos.empty
        ):
            raise ValueError("df_materiales_costos inválido o vacío")

        debug["df_materiales_costos"] = _preview_df(
            df_materiales_costos
        )
        entrada.df_costos_materiales = df_materiales_costos
        # =====================================================
        # 4. VALIDACIÓN ESTRUCTURAS
        # =====================================================
        if entrada.df_estructuras is None:
            raise ValueError("df_estructuras es None")

        if not isinstance(entrada.df_estructuras, pd.DataFrame):
            raise TypeError(
                f"df_estructuras no es DataFrame: {type(entrada.df_estructuras)}"
            )

        if entrada.df_estructuras.empty:
            raise ValueError("df_estructuras vacío")

        if entrada.df_materiales_por_estructura is None:
            raise ValueError("df_materiales_por_estructura es None")

        if not isinstance(
            entrada.df_materiales_por_estructura,
            dict
        ):
            raise TypeError(
                "df_materiales_por_estructura no es dict"
            )

        if len(entrada.df_materiales_por_estructura) == 0:
            raise ValueError(
                "df_materiales_por_estructura vacío"
            )

        debug["df_estructuras"] = _preview_df(
            entrada.df_estructuras
        )

        debug["materiales_por_estructura_keys"] = list(
            entrada.df_materiales_por_estructura.keys()
        )

        # =====================================================
        # 5. COSTOS POR ESTRUCTURA
        # =====================================================
        df_costos_estructura = (
            calcular_costos_por_estructura(
                df_estructuras=entrada.df_estructuras,

                df_materiales_por_estructura=(
                    entrada.df_materiales_por_estructura
                ),

                df_precios_materiales=df_costos
            )
        )

        if (
            df_costos_estructura is None
            or not isinstance(df_costos_estructura, pd.DataFrame)
            or df_costos_estructura.empty
        ):
            raise ValueError("df_costos_estructura inválido o vacío")

        debug["df_costos_estructura"] = _preview_df(
            df_costos_estructura
        )

        # =====================================================
        # 6. MANO DE OBRA
        # =====================================================
        df_mano_obra = None

        if entrada.df_estructuras is not None:

            try:

                res_mano_obra = calcular_mano_obra_proyecto(
                    df_estructuras_por_punto=entrada.df_estructuras,
                    df_cables=entrada.df_cables,
                    contratista=entrada.contratista
                )

                if not isinstance(res_mano_obra, dict):
                    raise TypeError(
                        f"calcular_mano_obra_proyecto no devolvió dict: {type(res_mano_obra)}"
                    )

                df_mano_obra = res_mano_obra.get(
                    "df_detalle"
                )

                debug["mano_obra_ok"] = res_mano_obra.get("ok")
                debug["mano_obra_keys"] = list(res_mano_obra.keys())
                debug["df_mano_obra"] = _preview_df(
                    df_mano_obra
                )

            except Exception as e:

                debug["mano_obra_error"] = (
                    f"{type(e).__name__}: {e}"
                )

        # =====================================================
        # 7. SUMINISTRO E INSTALACIÓN
        # =====================================================
        if df_mano_obra is None:
            raise ValueError(
                f"df_mano_obra es None. Error previo: {debug.get('mano_obra_error')}"
            )

        if not isinstance(df_mano_obra, pd.DataFrame):
            raise TypeError(
                f"df_mano_obra no es DataFrame: {type(df_mano_obra)}"
            )

        if df_mano_obra.empty:
            raise ValueError("df_mano_obra vacío")

        columnas_mano_obra = set(df_mano_obra.columns)

        if "Estructura" not in columnas_mano_obra:
            raise KeyError(
                f"df_mano_obra no tiene columna 'Estructura'. Columnas: {list(df_mano_obra.columns)}"
            )

        if "Precio" not in columnas_mano_obra:
            raise KeyError(
                f"df_mano_obra no tiene columna 'Precio'. Columnas: {list(df_mano_obra.columns)}"
            )

        columnas_costos_estructura = set(
            df_costos_estructura.columns
        )

        for col in [
            "codigodeestructura",
            "Cantidad",
            "Costo Unitario",
        ]:
            if col not in columnas_costos_estructura:
                raise KeyError(
                    f"df_costos_estructura no tiene columna '{col}'. Columnas: {list(df_costos_estructura.columns)}"
                )

        filas = []

        for _, r in df_costos_estructura.iterrows():

            estructura = str(
                r["codigodeestructura"]
            ).strip().upper()

            cantidad = max(
                1,
                int(r["Cantidad"])
            )

            material_unit = float(
                r["Costo Unitario"]
            )

            df_match = df_mano_obra[
                df_mano_obra["Estructura"]
                .astype(str)
                .str.strip()
                .str.upper()
                == estructura
            ]

            mano_obra_unit = (
                float(df_match["Precio"].iloc[0])
                if not df_match.empty
                else 0.0
            )

            total_unit = (
                material_unit
                + mano_obra_unit
            )

            total_proyecto = (
                total_unit
                * cantidad
            )

            filas.append({

                "Estructura": estructura,

                "Cantidad": cantidad,

                "Material Unitario": round(
                    material_unit,
                    2
                ),

                "Mano Obra Unitaria": round(
                    mano_obra_unit,
                    2
                ),

                "Total Unitario": round(
                    total_unit,
                    2
                ),

                "Total Proyecto": round(
                    total_proyecto,
                    2
                ),
            })

        # =====================================================
        # DATAFRAME FINAL
        # =====================================================
        df_precios_estructura = pd.DataFrame(
            filas
        )

        if df_precios_estructura.empty:
            raise ValueError("df_precios_estructura vacío")

        # =====================================================
        # CABLES
        # =====================================================
        df_precios_estructura = (
            _agregar_cable_a_precios(
                df_precios_estructura,
                entrada
            )
        )

        if (
            df_precios_estructura is None
            or not isinstance(df_precios_estructura, pd.DataFrame)
            or df_precios_estructura.empty
        ):
            raise ValueError(
                "df_precios_estructura inválido o vacío después de agregar cables"
            )

        # =====================================================
        # SUBTOTAL
        # =====================================================
        df_precios_estructura["Subtotal"] = (
            df_precios_estructura[
                "Total Proyecto"
            ]
        )

        total_proyecto = float(
            df_precios_estructura["Subtotal"].sum()
        )

        debug["total_proyecto"] = total_proyecto

        # =====================================================
        # DEBUG FINAL
        # =====================================================
        debug_guardar(
            "ORQUESTADOR_COSTOS_FINAL",
            {
                "precios": _preview_df(
                    df_precios_estructura
                ),
                "total_proyecto": total_proyecto,
            }
        )

        # =====================================================
        # OUTPUT
        # =====================================================
        return {

            "ok": True,

            "df_costos_materiales": (
                df_materiales_costos
            ),

            "df_costos_estructura": (
                df_costos_estructura
            ),

            "df_mano_obra": (
                df_mano_obra
            ),

            "df_precios_estructura": (
                df_precios_estructura
            ),

            "total_materiales": total_proyecto,

            "total_proyecto": total_proyecto,

            "debug": debug
        }

    except Exception as e:
        import traceback

        error_msg = f"{type(e).__name__}: {e}"
        traceback_txt = traceback.format_exc()

        debug["EXCEPTION"] = error_msg
        debug["TRACEBACK"] = traceback_txt

        return {
            "ok": False,
            "error": error_msg,
            "traceback": traceback_txt,
            "errores": [error_msg],

            "df_costos_materiales": None,
            "df_costos_estructura": None,
            "df_mano_obra": None,
            "df_precios_estructura": None,
            "df_resumen_costos": None,

            "total_materiales": 0.0,
            "total_proyecto": 0.0,

            "debug": debug,
        }
