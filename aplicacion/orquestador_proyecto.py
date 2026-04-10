# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional, Dict, Any
import traceback
import pandas as pd

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


def _safe_list(x):
    return x if isinstance(x, list) else []


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

    if not isinstance(salida_interfaz, SalidaInterfaz):
        return _fail("salida_interfaz inválida")

    if not salida_interfaz.ok:
        return _fail("SalidaInterfaz no válida")

    try:
        # =====================================================
        # 1. ENTRADAS
        # =====================================================
        salida_entradas = ejecutar_entradas(salida_interfaz)

        if not salida_entradas or not salida_entradas.ok:
            return _fail("Error en entradas")

        df_estructuras = _adaptar_df_estructuras(
            salida_entradas.df_estructuras
        )

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
            estructuras_df=entrada_proyecto.df_estructuras,
            tension=tension,
            base_datos=entrada_proyecto.base_datos,
            datos_proyecto=entrada_proyecto.datos_proyecto,
            df_cables=entrada_proyecto.df_cables,
            df_materiales_extra=entrada_proyecto.df_materiales_extra,
            calibre_mt=entrada_proyecto.calibre_mt,
            tabla_conectores_mt=entrada_proyecto.tabla_conectores_mt,
        )

        resultado_materiales = ejecutar_materiales(entrada_mat)

        if not resultado_materiales or not resultado_materiales.ok:
            return _fail("Error en materiales")

        # =====================================================
        # 4. COSTOS (ARREGLADO)
        # =====================================================
        df_materiales = resultado_materiales.df_materiales

        df_catalogo = obtener_catalogo_materiales(
            entrada_proyecto.base_datos
        )

        if df_catalogo is None or df_catalogo.empty:
            raise ValueError("Catálogo vacío")

        entrada_costos = EntradaCostos(
            df_materiales=df_materiales,
            df_catalogo=df_catalogo
        )

        resultado_costos = ejecutar_costos(entrada_costos)

        # =====================================================
        # 5. REPORTES
        # =====================================================
        resultado_reportes = generar_reportes({
            "df_estructuras": entrada_proyecto.df_estructuras,
            "df_materiales": resultado_materiales.df_materiales,
            "costos": resultado_costos,
        })

        # =====================================================
        # 6. SALIDA
        # =====================================================
        return ResultadoProyecto(
            ok=True,
            errores=[],
            warnings=[],
            materiales=resultado_materiales,
            costos=resultado_costos,
            reportes=resultado_reportes,
            debug=debug_global
        )

    except Exception as e:

        debug_global["exception"] = {
            "error": str(e),
            "trace": traceback.format_exc()
        }

        return ResultadoProyecto(
            ok=False,
            errores=[str(e)],
            warnings=[],
            materiales=None,
            costos=None,
            reportes=None,
            debug=debug_global,
        )
