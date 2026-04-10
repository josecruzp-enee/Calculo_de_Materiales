# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional, Dict, Any
import traceback
import pandas as pd
from ayuda.debug import debug_guardar
# =========================================================
# CONTRATOS
# =========================================================
from interfaz.contratos import ResultadoProyecto, SalidaInterfaz
from aplicacion.modelos_proyecto import EntradaProyecto

# =========================================================
# DOMINIO
# =========================================================
from entradas.orquestador_entradas import ejecutar_entradas
from entradas.base_datos import obtener_catalogo_materiales

from materiales.modelos.entrada import EntradaMateriales
from materiales.orquestador_materiales import ejecutar_materiales

from costos_precios.orquestador_costos import (
    ejecutar_costos,
    EntradaCostos,
)

from costos_precios.costos_estructuras import calcular_costos_por_estructura
from exportadores.orquestador_reportes import generar_reportes


# =========================================================
# HELPERS
# =========================================================
def _fail(msg: str, debug: Optional[dict] = None) -> ResultadoProyecto:
    return ResultadoProyecto(
        ok=False,
        errores=[msg],
        warnings=[],
        materiales=None,
        costos=None,
        reportes=None,
        debug=debug or {},
    )


def _extraer_tension(datos: Dict[str, Any]) -> float:
    t = datos.get("tension") or datos.get("nivel_de_tension")

    if t is None:
        raise ValueError("Tensión no definida")

    t = float(t)

    if t <= 0:
        raise ValueError("Tensión inválida")

    return t


def _adaptar_df_estructuras(df: pd.DataFrame) -> pd.DataFrame:

    if df is None:
        raise ValueError("df_estructuras es None")

    df = df.copy()
    cols = set(df.columns)

    if {"Estructura", "Cantidad"}.issubset(cols):
        return df

    if {"codigodeestructura", "Cantidad"}.issubset(cols):
        return df.rename(columns={"codigodeestructura": "Estructura"})

    raise ValueError(f"df_estructuras inválido: {list(cols)}")


# =========================================================
# ORQUESTADOR
# =========================================================
def ejecutar_proyecto(salida_interfaz: SalidaInterfaz) -> ResultadoProyecto:

    debug_global: Dict[str, Any] = {}

    try:

        # =====================================================
        # 0. INTERFAZ
        # =====================================================
        debug_global["interfaz"] = {
            "ok": getattr(salida_interfaz, "ok", None),
            "tipo_entrada": getattr(salida_interfaz, "tipo_entrada", None),
            "datos_proyecto_keys": list((salida_interfaz.datos_proyecto or {}).keys())
        }

        if not salida_interfaz.ok:
            return _fail("SalidaInterfaz no válida", debug_global)

        # =====================================================
        # 1. ENTRADAS
        # =====================================================
        salida_entradas = ejecutar_entradas(salida_interfaz)

        df_estructuras = _adaptar_df_estructuras(
            salida_entradas.df_estructuras
        )
        debug_guardar("DEBUG_ENTRADAS_REAL", {
            "tipo_df_estructuras": str(type(salida_entradas.df_estructuras)),
            "es_dataframe": isinstance(salida_entradas.df_estructuras, pd.DataFrame),
        })
        # =====================================================
        # 2. PROYECTO
        # =====================================================
        entrada_proyecto = EntradaProyecto(
            base_datos=salida_entradas.base_datos,
            df_estructuras=df_estructuras,
            datos_proyecto=salida_entradas.datos_proyecto,
            calibre_mt=(salida_entradas.datos_proyecto or {}).get("calibre_mt", ""),
            tabla_conectores_mt=(salida_entradas.datos_proyecto or {}).get("tabla_conectores_mt", {}),
            df_cables=salida_entradas.df_cables,
            df_materiales_extra=salida_entradas.df_materiales_extra,
        )

        entrada_proyecto.validar()
        tension = _extraer_tension(entrada_proyecto.datos_proyecto)

        # =====================================================
        # 3. MATERIALES
        # =====================================================
        entrada_mat = EntradaMateriales(
            estructuras_df=df_estructuras,
            tension=tension,
            base_datos=entrada_proyecto.base_datos,
            datos_proyecto=entrada_proyecto.datos_proyecto,
            df_cables=entrada_proyecto.df_cables,
            df_materiales_extra=entrada_proyecto.df_materiales_extra,
            calibre_mt=entrada_proyecto.calibre_mt,
            tabla_conectores_mt=entrada_proyecto.tabla_conectores_mt,
        )

        resultado_materiales = ejecutar_materiales(entrada_mat)
        df_materiales = resultado_materiales.df_materiales

        # =====================================================
        # 4. CATÁLOGO
        # =====================================================
        df_catalogo = obtener_catalogo_materiales(
            entrada_proyecto.base_datos
        )

        # =====================================================
        # 5. COSTOS GLOBALES
        # =====================================================
        debug_guardar("CHECK_MATERIALES_ESTRUCTURA", {
            "es_dict": isinstance(resultado_materiales.df_materiales_por_estructura, dict),
            "keys": list(resultado_materiales.df_materiales_por_estructura.keys()) 
            if isinstance(resultado_materiales.df_materiales_por_estructura, dict) else "NO",
        })
        entrada_costos = EntradaCostos(
            df_materiales=df_materiales,
            df_catalogo=df_catalogo,
            df_estructuras=df_estructuras,
            df_materiales_por_estructura=resultado_materiales.df_materiales_por_estructura,
        )

        resultado_costos = ejecutar_costos(entrada_costos)

        # =====================================================
        # 🔥 6. COSTOS POR ESTRUCTURA (FIX SEGURO)
        # =====================================================

        df_costos_estructura = None

        try:
            df_costos_estructura = calcular_costos_por_estructura(
                df_estructuras=df_estructuras,
                df_materiales_por_estructura=resultado_materiales.df_materiales_por_estructura,
                df_precios_materiales=df_catalogo
            )
            

            total = 0.0

            if (
                df_costos_estructura is not None
                and "Costo Total" in df_costos_estructura.columns
            ):
                total = float(df_costos_estructura["Costo Total"].sum())

            debug_global["costos_estructura_total"] = total

            debug_global["costos_estructura"] = {
                "ok": True,
                "shape": list(df_costos_estructura.shape)
                if df_costos_estructura is not None else None
            }

        except Exception as e:

            debug_global["costos_estructura"] = {
                "ok": False,
                "error": str(e)
            }

            debug_global["costos_estructura_total"] = 0

        # =====================================================
        # 7. REPORTES
        # =====================================================
        resultado_reportes = generar_reportes({
            "df_estructuras": df_estructuras,
            "df_materiales": df_materiales,
            "costos": resultado_costos,
            "costos_estructura": df_costos_estructura,
        })

        # =====================================================
        # 8. SALIDA
        # =====================================================
        return ResultadoProyecto(
            ok=True,
            errores=[],
            warnings=[],
            materiales=resultado_materiales,
            costos=resultado_costos,
            df_costos_estructura=df_costos_estructura,
            reportes=resultado_reportes,
            debug=debug_global
        )

    except Exception as e:

        debug_global["exception"] = {
            "error": str(e),
            "trace": traceback.format_exc()
        }

        return _fail(str(e), debug_global)
