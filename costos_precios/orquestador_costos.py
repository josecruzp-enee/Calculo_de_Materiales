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

from costos_precios.costos_operativos import calcular_costos_operativos
from costos_precios.precio_estructura import calcular_precio_estructura
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

    ruta_datos_materiales: Optional[str] = None  # 🔥 NUEVO (para MO)
    df_cables: Optional[pd.DataFrame] = None 

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


def calcular_costos_cable(df_cables):

    total = 0

    for _, r in df_cables.iterrows():

        tipo = r["tipo"]   # PRIMARIO / SECUNDARIO
        longitud = float(r["longitud"])

        if tipo == "PRIMARIO":
            precio = 120   # INST-LP
        else:
            precio = 80    # INST-LS

        total += longitud * precio

    return total

# =====================================================
# ORQUESTADOR PRINCIPAL
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
        # 2. CATÁLOGO
        # =====================================================
        df_costos = preparar_catalogo_costos(entrada.df_catalogo)

        if df_costos is None or df_costos.empty:
            raise ValueError("df_costos vacío")

        debug["catalogo_procesado"] = _preview_df(df_costos)

        # =====================================================
        # 3. COSTOS DE MATERIALES
        # =====================================================
        df_materiales_costos = calcular_lista_materiales_con_costos(
            df_materiales=entrada.df_materiales,
            df_catalogo_costos=df_costos
        )

        debug["materiales_costos"] = _preview_df(df_materiales_costos)

        # =====================================================
        # 4. COSTOS POR ESTRUCTURA
        # =====================================================
        df_costos_estructura = None

        if (
            entrada.df_estructuras is not None and
            entrada.df_materiales_por_estructura is not None
        ):
            df_costos_estructura = calcular_costos_por_estructura(
                df_estructuras=entrada.df_estructuras,
                df_materiales_por_estructura=entrada.df_materiales_por_estructura,
                df_precios_materiales=df_costos
            )

            debug["costos_estructura"] = _preview_df(df_costos_estructura)

        # =====================================================
        # 5. MANO DE OBRA (OPCIONAL - NO BLOQUEANTE)
        # =====================================================
        df_mano_obra = None

        if df_costos_estructura is not None:

            if entrada.ruta_datos_materiales:
                try:
                    df_mano_obra = calcular_mano_obra(
                        df_estructuras=entrada.df_estructuras,
                        archivo_materiales=entrada.ruta_datos_materiales
                    )
                except Exception as e:
                    debug["mano_obra_error"] = str(e)
                    df_mano_obra = None

            debug["mano_obra"] = _preview_df(df_mano_obra)

        # =====================================================
        # 6. PRECIOS POR ESTRUCTURA (DESACOPLADO)
        # =====================================================
        df_precios_estructura = None

        if df_costos_estructura is not None:

            material_total = df_costos_estructura["Costo Total"].sum()

            # 🔥 SI NO HAY MO → USAR 0
            if df_mano_obra is not None:
                mo_total = df_mano_obra["MO Total"].sum()
            else:
                mo_total = 0.0

            costos_op = calcular_costos_operativos(
                costo_material_total=material_total,
                costo_mano_obra=mo_total
            )

            filas = []

            for _, r in df_costos_estructura.iterrows():

                estructura = str(r["codigodeestructura"]).strip()
                costo_mat_unit = float(r["Costo Unitario"])
                costo_total_estructura = float(r["Costo Total"])
                cantidad = max(1, int(r["Cantidad"]))

                if material_total <= 0:
                    continue

                peso = costo_total_estructura / material_total

                costo_operativo_unit = (
                    costos_op.operativo_total * peso
                ) / cantidad

                res = calcular_precio_estructura(
                    estructura=estructura,
                    costo_materiales=costo_mat_unit,
                    costo_operativo=costo_operativo_unit,
                    porcentaje_utilidad=0.25,
                )

                filas.append({
                    "Estructura": estructura,
                    "Cantidad": cantidad,
                    "Costo Unitario": costo_mat_unit,
                    "Costo Operativo": costo_operativo_unit,
                    "Precio Unitario": res.precio_unitario,
                    "Precio Total": res.precio_unitario * cantidad,
                })

            df_precios_estructura = pd.DataFrame(filas)

            debug["precios_estructura"] = _preview_df(df_precios_estructura)

        # =====================================================
        # 7. MÉTRICAS
        # =====================================================
        total_materiales = float(df_materiales_costos["Costo Total"].sum())

        total_estructura = 0.0
        if df_costos_estructura is not None:
            total_estructura = float(df_costos_estructura["Costo Total"].sum())

        total_precio = 0.0
        if df_precios_estructura is not None:
            total_precio = float(df_precios_estructura["Precio Total"].sum())

        # =====================================================
        # 🔥 COSTO DE CABLE (NUEVO)
        # =====================================================
        total_cable = 0.0

        if "df_cables" in locals() and df_cables is not None and not df_cables.empty:

            # Ajusta nombres de columnas según tu df real
            for _, r in df_cables.iterrows():

                tipo = str(r.get("tipo", "")).upper()
                longitud = float(r.get("longitud", 0))

                # 🔥 precios que ya definiste
                if tipo == "PRIMARIO":
                    precio_inst = 120   # INST-LP
                else:
                    precio_inst = 80    # INST-LS

                # 👉 si tienes precio de material por metro, súmalo aquí
                precio_material = float(r.get("precio_material_m", 0))

                total_cable += longitud * (precio_inst + precio_material)

        # =====================================================
        # 🔥 ACTUALIZAR TOTAL PROYECTO
        # =====================================================
        total_precio = total_precio + total_cable




        
        debug["metricas"] = {
            "materiales": total_materiales,
            "estructuras": total_estructura,
            "precio_total": total_precio
        }

        debug_guardar("ORQUESTADOR_COSTOS_FINAL", debug)

        return {
            "ok": True,
            "df_materiales_costos": df_materiales_costos,
            "df_costos_estructura": df_costos_estructura,
            "df_mano_obra": df_mano_obra,
            "df_precios_estructura": df_precios_estructura,
            "debug": debug
        }

    except Exception as e:

        debug["error"] = str(e)
        debug_guardar("ORQUESTADOR_COSTOS_ERROR", debug)

        return {
            "ok": False,
            "errores": [str(e)],
            "df_materiales_costos": None,
            "df_costos_estructura": None,
            "df_mano_obra": None,
            "df_precios_estructura": None,
            "debug": debug
        }
