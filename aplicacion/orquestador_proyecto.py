# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional

# =========================================================
# CONTRATOS
# =========================================================
from interfaz.contratos import ResultadoProyecto, SalidaInterfaz

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
        # 2. CONTEXTO (TENSIÓN)
        # =====================================================
        datos_proyecto = salida_entradas.datos_proyecto or {}

        if not datos_proyecto:
            return _fail("datos_proyecto vacío")

        try:
            tension = float(
                datos_proyecto.get("tension")
                or datos_proyecto.get("nivel_de_tension")
            )
        except (TypeError, ValueError):
            return _fail("Tensión inválida o no numérica")

        # =====================================================
        # 3. MATERIALES
        # =====================================================
        entrada_mat = EntradaMateriales(
            estructuras_df=salida_entradas.df_estructuras,
            tension=tension,
            base_datos=salida_entradas.base_datos,
            datos_proyecto=datos_proyecto,
            df_cables=salida_entradas.df_cables,
            df_materiales_extra=salida_entradas.df_materiales_extra,
            calibre_mt=getattr(salida_entradas, "calibre_mt", None),
            tabla_conectores_mt=getattr(salida_entradas, "tabla_conectores_mt", None),
        )

        resultado_materiales = ejecutar_materiales(entrada_mat)

        if not resultado_materiales or not resultado_materiales.ok:
            return _fail(
                "Error en materiales",
                debug={"errores": getattr(resultado_materiales, "errores", [])},
            )

        # =====================================================
        # 4. COSTOS
        # =====================================================
        df_ep = resultado_materiales.df_estructuras_por_punto

        if df_ep is None:
            return _fail("df_estructuras_por_punto no disponible para costos")

        fuente_precios = getattr(salida_entradas, "df_precios_materiales", None)
        df_costos_est = getattr(salida_entradas, "df_costos_estructuras", None)

        if fuente_precios is None:
            return _fail("No se proporcionó fuente de precios")

        if df_costos_est is None:
            return _fail("No se proporcionó df_costos_estructuras")

        entrada_costos = EntradaCostos(
            df_resumen=resultado_materiales.df_materiales,
            df_estructuras_por_punto=df_ep,
            df_costos_estructuras=df_costos_est,
            fuente_precios=fuente_precios,
        )

        resultado_costos = ejecutar_costos(entrada_costos)

        if not resultado_costos or not resultado_costos.ok:
            return _fail(
                "Error en costos",
                debug={"errores": getattr(resultado_costos, "errores", [])},
            )

        # =====================================================
        # 5. REPORTES
        # =====================================================
        data_reportes = {
            "df_estructuras": salida_entradas.df_estructuras,
            "df_materiales": resultado_materiales.df_materiales,
            "df_resumen": resultado_materiales.df_materiales,
            "df_por_punto": resultado_materiales.df_materiales_por_punto,
            "costos": resultado_costos,
        }

        resultado_reportes = generar_reportes(data_reportes)

        if not isinstance(resultado_reportes, dict):
            return _fail("Salida de reportes inválida")

        # =====================================================
        # 6. CONSOLIDACIÓN
        # =====================================================
        warnings = []
        warnings += _safe_list(getattr(salida_entradas, "warnings", []))
        warnings += _safe_list(getattr(resultado_materiales, "warnings", []))
        warnings += _safe_list(getattr(resultado_costos, "warnings", []))

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
        import traceback

        return ResultadoProyecto(
            ok=False,
            errores=[str(e)],
            warnings=[],
            materiales=None,
            costos=None,
            reportes=None,
            debug={"traceback": traceback.format_exc()},
        )
