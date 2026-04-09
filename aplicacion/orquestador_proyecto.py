# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional, Dict, Any
import traceback
import pandas as pd
from costos_precios.costos_materiales import construir_entrada_costos
# =========================================================
# CONTRATOS
# =========================================================
from interfaz.contratos import ResultadoProyecto, SalidaInterfaz
from aplicacion.modelos_proyecto import EntradaProyecto

# =========================================================
# ORQUESTADORES DOMINIO
# =========================================================
from entradas.orquestador_entradas import ejecutar_entradas

from materiales.modelos.entrada import EntradaMateriales
from materiales.orquestador_materiales import ejecutar_materiales
from costos_precios.costos_materiales import construir_entrada_costos
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
        raise ValueError("Tensión no definida en datos_proyecto")

    try:
        t = float(t)
    except Exception:
        raise ValueError(f"Tensión inválida: {t}")

    if t <= 0:
        raise ValueError("Tensión debe ser mayor a 0")

    return t


# =========================================================
# ADAPTADOR DF ESTRUCTURAS
# =========================================================
def _adaptar_df_estructuras(df: pd.DataFrame) -> pd.DataFrame:

    if df is None:
        raise ValueError("df_estructuras es None desde Entradas")

    if not isinstance(df, pd.DataFrame):
        raise TypeError("df_estructuras no es DataFrame")

    df = df.copy()
    cols = set(df.columns)

    # ✔ Caso correcto
    if {"Estructura", "Cantidad"}.issubset(cols):
        return df

    # ✔ Caso DXF (tu caso actual)
    if {"codigodeestructura", "Cantidad"}.issubset(cols):
        df = df.rename(columns={
            "codigodeestructura": "Estructura"
        })
        return df

    raise ValueError(
        f"df_estructuras inválido. Columnas recibidas: {list(cols)}"
    )


# =========================================================
# ORQUESTADOR PRINCIPAL
# =========================================================
def ejecutar_proyecto(salida_interfaz: SalidaInterfaz) -> ResultadoProyecto:

    debug_global: Dict[str, Any] = {}

    # =====================================================
    # VALIDACIÓN INICIAL
    # =====================================================
    if not isinstance(salida_interfaz, SalidaInterfaz):
        return _fail("salida_interfaz debe ser SalidaInterfaz")

    debug_global["interfaz"] = getattr(salida_interfaz, "debug", {})

    if not salida_interfaz.ok:
        return _fail("SalidaInterfaz no válida", debug=debug_global)

    try:
        # =====================================================
        # 1. ENTRADAS
        # =====================================================
        salida_entradas = ejecutar_entradas(salida_interfaz)

        debug_global["entradas"] = getattr(salida_entradas, "debug", {})

        if not salida_entradas or not salida_entradas.ok:
            return _fail("Error en entradas", debug=debug_global)

        # 🔴 VALIDACIÓN CRÍTICA
        if salida_entradas.df_estructuras is None:
            raise ValueError("Entradas no generó df_estructuras")

        if not isinstance(salida_entradas.df_estructuras, pd.DataFrame):
            raise TypeError("df_estructuras no es DataFrame desde Entradas")

        debug_global["entradas_df"] = {
            "columnas": list(salida_entradas.df_estructuras.columns),
            "filas": len(salida_entradas.df_estructuras)
        }

        # =====================================================
        # 2. ADAPTACIÓN CONTRATO
        # =====================================================
        df_estructuras = _adaptar_df_estructuras(
            salida_entradas.df_estructuras
        )

        debug_global["df_estructuras_adaptado"] = {
            "columnas": list(df_estructuras.columns),
            "filas": len(df_estructuras)
        }

        # =====================================================
        # 3. CONTRATO PROYECTO
        # =====================================================
        entrada_proyecto = EntradaProyecto(
            base_datos=salida_entradas.base_datos,
            df_estructuras=df_estructuras,
            datos_proyecto=salida_entradas.datos_proyecto,

            calibre_mt=(salida_entradas.datos_proyecto or {}).get("calibre_mt", ""),
            tabla_conectores_mt=(salida_entradas.datos_proyecto or {}).get("tabla_conectores_mt", {}),

            df_cables=salida_entradas.df_cables,
            df_materiales_extra=salida_entradas.df_materiales_extra,

            df_precios_materiales=(salida_entradas.datos_proyecto or {}).get("df_precios_materiales"),
            df_costos_estructuras=(salida_entradas.datos_proyecto or {}).get("df_costos_estructuras"),
        )

        entrada_proyecto.validar()

        # =====================================================
        # 4. CONTEXTO
        # =====================================================
        tension = _extraer_tension(entrada_proyecto.datos_proyecto)

        debug_global["contexto"] = {
            "tension": tension
        }

        # =====================================================
        # 5. MATERIALES
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

        debug_global["materiales"] = getattr(resultado_materiales, "debug", {})

        if not resultado_materiales or not resultado_materiales.ok:
            return _fail("Error en materiales", debug=debug_global)

        # =====================================================
        # 6. COSTOS
        # =====================================================
        # =====================================================
        # 6. COSTOS (AUTO DESDE CATÁLOGO)
        # =====================================================
        df_ep = resultado_materiales.df_estructuras_por_punto

        if df_ep is None:
            return _fail("df_estructuras_por_punto no disponible", debug=debug_global)

        if entrada_proyecto.df_costos_estructuras is None:
            return _fail("df_costos_estructuras requerido", debug=debug_global)

        # 🔥 CONSTRUIR PRECIOS DESDE BASE_DATOS
        entrada_costos = construir_entrada_costos(
            data=entrada_proyecto.base_datos,
            df_resumen=resultado_materiales.df_materiales,
            df_estructuras_por_punto=df_ep,
            df_costos_estructuras=entrada_proyecto.df_costos_estructuras,
        )

        resultado_costos = ejecutar_costos(entrada_costos)

        # =====================================================
        # 7. REPORTES
        # =====================================================
        resultado_reportes = generar_reportes({
            "df_estructuras": entrada_proyecto.df_estructuras,
            "df_materiales": resultado_materiales.df_materiales,
            "df_resumen": resultado_materiales.df_materiales,
            "df_por_punto": resultado_materiales.df_materiales_por_punto,
            "costos": resultado_costos,
        })

        if not isinstance(resultado_reportes, dict):
            return _fail("Salida de reportes inválida", debug=debug_global)

        debug_global["reportes"] = {
            "archivos": list(resultado_reportes.keys())
        }

        # =====================================================
        # 8. CONSOLIDACIÓN
        # =====================================================
        warnings = (
            _safe_list(salida_entradas.warnings) +
            _safe_list(resultado_materiales.warnings) +
            _safe_list(resultado_costos.warnings)
        )

        return ResultadoProyecto(
            ok=True,
            errores=[],
            warnings=warnings,
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
