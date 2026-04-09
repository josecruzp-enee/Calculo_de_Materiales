# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional, Dict, Any
import traceback

# =========================================================
# CONTRATOS
# =========================================================
from interfaz.contratos import ResultadoProyecto, SalidaInterfaz
from aplicacion.contratos import EntradaProyecto

# =========================================================
# ORQUESTADORES
# =========================================================
from entradas.orquestador_entradas import ejecutar_entradas
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
        raise ValueError("Tensión no definida en datos_proyecto")

    try:
        t = float(t)
    except Exception:
        raise ValueError(f"Tensión inválida: {t}")

    if t <= 0:
        raise ValueError("Tensión debe ser mayor a 0")

    return t


# =========================================================
# ORQUESTADOR PRINCIPAL
# =========================================================
def ejecutar_proyecto(salida_interfaz: SalidaInterfaz) -> ResultadoProyecto:

    # =====================================================
    # VALIDACIÓN INICIAL
    # =====================================================
    if not isinstance(salida_interfaz, SalidaInterfaz):
        return _fail("salida_interfaz debe ser SalidaInterfaz")

    if not salida_interfaz.ok:
        return _fail(
            "SalidaInterfaz no válida",
            debug={"errores_interfaz": salida_interfaz.errores},
        )

    try:
        # =====================================================
        # 1. ENTRADAS
        # =====================================================
        salida_entradas = ejecutar_entradas(salida_interfaz)

        if not salida_entradas or not salida_entradas.ok:
            return _fail(
                "Error en entradas",
                debug={"errores": getattr(salida_entradas, "errores", [])},
            )

        # =====================================================
        # 2. CONSTRUCCIÓN CONTRATO PROYECTO (SIN getattr)
        # =====================================================
        entrada_proyecto = EntradaProyecto(
            base_datos=salida_entradas.base_datos,
            df_estructuras=salida_entradas.df_estructuras,
            datos_proyecto=salida_entradas.datos_proyecto,

            calibre_mt=salida_entradas.calibre_mt or "",
            tabla_conectores_mt=salida_entradas.tabla_conectores_mt or {}
            

            df_cables=salida_entradas.df_cables,
            df_materiales_extra=salida_entradas.df_materiales_extra,

            df_precios_materiales=salida_entradas.df_precios_materiales,
            df_costos_estructuras=salida_entradas.df_costos_estructuras,
        )

        # =====================================================
        # 3. VALIDACIÓN FUERTE
        # =====================================================
        entrada_proyecto.validar()

        # =====================================================
        # 4. CONTEXTO
        # =====================================================
        tension = _extraer_tension(entrada_proyecto.datos_proyecto)

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

        if not resultado_materiales or not resultado_materiales.ok:
            return _fail(
                "Error en materiales",
                debug={"errores": resultado_materiales.errores},
            )

        # =====================================================
        # 6. COSTOS
        # =====================================================
        df_ep = resultado_materiales.df_estructuras_por_punto

        if df_ep is None:
            return _fail("df_estructuras_por_punto no disponible")

        if entrada_proyecto.df_precios_materiales is None:
            return _fail("df_precios_materiales requerido")

        if entrada_proyecto.df_costos_estructuras is None:
            return _fail("df_costos_estructuras requerido")

        entrada_costos = EntradaCostos(
            df_resumen=resultado_materiales.df_materiales,
            df_estructuras_por_punto=df_ep,
            df_costos_estructuras=entrada_proyecto.df_costos_estructuras,
            fuente_precios=entrada_proyecto.df_precios_materiales,
        )

        resultado_costos = ejecutar_costos(entrada_costos)

        if not resultado_costos or not resultado_costos.ok:
            return _fail(
                "Error en costos",
                debug={"errores": resultado_costos.errores},
            )

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
            return _fail("Salida de reportes inválida")

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
            debug={
                "fase": "completo",
                "tension": tension,
            },
        )

    except Exception as e:
        return ResultadoProyecto(
            ok=False,
            errores=[str(e)],
            warnings=[],
            materiales=None,
            costos=None,
            reportes=None,
            debug={
                "traceback": traceback.format_exc(),
                "fase": "exception",
            },
        )
