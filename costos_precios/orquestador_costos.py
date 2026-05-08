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
from costos_precios.costos_mano_obra import calcular_mano_obra

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

        # =====================================================
        # 3. COSTOS DE MATERIALES
        # =====================================================
        df_materiales_costos = (
            calcular_lista_materiales_con_costos(
                df_materiales=entrada.df_materiales,
                df_catalogo_costos=df_costos
            )
        )

        # =====================================================
        # 4. VALIDACIÓN
        # =====================================================
        if (
            entrada.df_estructuras is None
            or entrada.df_materiales_por_estructura is None
            or not isinstance(
                entrada.df_materiales_por_estructura,
                dict
            )
        ):
            raise ValueError(
                "df_materiales_por_estructura inválido"
            )

        if len(entrada.df_materiales_por_estructura) == 0:
            raise ValueError(
                "df_materiales_por_estructura vacío"
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

        debug["df_costos_estructura"] = _preview_df(
            df_costos_estructura
        )

        # =====================================================
        # 6. MANO DE OBRA
        # =====================================================
        df_mano_obra = None

        if entrada.ruta_datos_materiales:

            try:

                df_mano_obra = calcular_mano_obra(
                    df_estructuras=entrada.df_estructuras,

                    archivo_materiales=(
                        entrada.ruta_datos_materiales
                    )
                )

                debug["df_mano_obra"] = _preview_df(
                    df_mano_obra
                )

            except Exception as e:

                debug["mano_obra_error"] = str(e)

        # =====================================================
        # 7. SUMINISTRO E INSTALACIÓN
        # =====================================================
        filas = []

        # -----------------------------------------------------
        # MAPA MANO OBRA
        # -----------------------------------------------------
        mapa_mo = {}

        if (
            df_mano_obra is not None
            and not df_mano_obra.empty
        ):

            for _, mo in df_mano_obra.iterrows():

                cod = str(
                    mo.get(
                        "Estructura",
                        ""
                    )
                ).strip().upper()

                mapa_mo[cod] = float(
                    mo.get(
                        "Precio",
                        0
                    )
                )

        debug["mapa_mo"] = list(
            mapa_mo.items()
        )[:10]

        # -----------------------------------------------------
        # LOOP PRINCIPAL
        # -----------------------------------------------------
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

            mano_obra_unit = mapa_mo.get(
                estructura,
                0.0
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

        # =====================================================
        # CABLES
        # =====================================================
        df_precios_estructura = (
            _agregar_cable_a_precios(
                df_precios_estructura,
                entrada
            )
        )

        # =====================================================
        # SUBTOTAL
        # =====================================================
        if not df_precios_estructura.empty:

            df_precios_estructura["Subtotal"] = (
                df_precios_estructura[
                    "Total Proyecto"
                ]
            )

        # =====================================================
        # DEBUG FINAL
        # =====================================================
        debug_guardar(
            "ORQUESTADOR_COSTOS_FINAL",
            {
                "precios": _preview_df(
                    df_precios_estructura
                )
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

            "debug": debug
        }

    except Exception as e:

        debug["error"] = str(e)

        debug_guardar(
            "ORQUESTADOR_COSTOS_ERROR",
            debug
        )

        return {

            "ok": False,

            "errores": [str(e)],

            "df_materiales_costos": None,

            "df_costos_estructura": None,

            "df_mano_obra": None,

            "df_precios_estructura": None,

            "debug": debug
        }
