# -*- coding: utf-8 -*-
# aplicacion/orquestador_proyecto.py

from __future__ import annotations

from typing import Dict, Any
import traceback

# =========================================================
# CONTRATOS
# =========================================================
from interfaz.contratos import (
    SalidaInterfaz,
    SalidaEntradas,
    SalidaCostos,
    ResultadoProyecto,
)

from materiales.modelos.salida import SalidaMateriales

# =========================================================
# DOMINIOS
# =========================================================
from entradas.orquestador_entradas import ejecutar_entradas
from materiales.orquestador_materiales import ejecutar_materiales
from costos_precios.orquestador_costos import ejecutar_costos
from exportadores.orquestador_reportes import generar_reportes


# =========================================================
# HELPERS DEBUG
# =========================================================
def _debug_block(nombre: str, input_data: Dict, output_data: Dict, estado: Dict):
    return {
        "etapa": nombre,
        "input": input_data,
        "output": output_data,
        "estado": estado,
    }


# =========================================================
# ORQUESTADOR PRINCIPAL
# =========================================================
def ejecutar_proyecto(entrada_ui: SalidaInterfaz) -> ResultadoProyecto:

    debug_global: Dict[str, Any] = {}

    try:
        # =====================================================
        # VALIDACIÓN INICIAL
        # =====================================================
        if not entrada_ui.ok:
            return ResultadoProyecto(
                ok=False,
                errores=entrada_ui.errores,
                warnings=[],
                debug={"interfaz": entrada_ui.debug},
            )

        # =====================================================
        # 🔷 1. ENTRADAS
        # =====================================================
        salida_entradas: SalidaEntradas = ejecutar_entradas(entrada_ui)

        debug_global["entradas"] = _debug_block(
            "entradas",
            input_data={
                "tipo_entrada": entrada_ui.tipo_entrada,
                "tiene_data": entrada_ui.data_entrada is not None,
            },
            output_data={
                "filas_estructuras": len(salida_entradas.df_estructuras)
                if salida_entradas.df_estructuras is not None else 0,
                "columnas": list(salida_entradas.df_estructuras.columns)
                if salida_entradas.df_estructuras is not None else [],
            },
            estado={
                "ok": salida_entradas.ok,
                "errores": salida_entradas.errores,
                "warnings": salida_entradas.warnings,
            }
        )

        if not salida_entradas.ok:
            return ResultadoProyecto(
                ok=False,
                errores=salida_entradas.errores,
                warnings=salida_entradas.warnings,
                debug=debug_global,
            )

        # =====================================================
        # 🔷 2. MATERIALES
        # =====================================================
        salida_materiales: SalidaMateriales = ejecutar_materiales(salida_entradas)

        debug_global["materiales"] = _debug_block(
            "materiales",
            input_data={
                "estructuras_recibidas": len(salida_entradas.df_estructuras),
            },
            output_data={
                "materiales_total": len(salida_materiales.df_materiales)
                if hasattr(salida_materiales, "df_materiales") else 0,
            },
            estado={
                "ok": salida_materiales.ok,
                "errores": salida_materiales.errores,
                "warnings": salida_materiales.warnings,
            }
        )

        if not salida_materiales.ok:
            return ResultadoProyecto(
                ok=False,
                errores=salida_materiales.errores,
                warnings=salida_materiales.warnings,
                materiales=salida_materiales,
                debug=debug_global,
            )

        # =====================================================
        # 🔷 3. COSTOS
        # =====================================================
        salida_costos: SalidaCostos = ejecutar_costos(salida_materiales)

        debug_global["costos"] = _debug_block(
            "costos",
            input_data={
                "materiales": len(salida_materiales.df_materiales)
                if hasattr(salida_materiales, "df_materiales") else 0,
            },
            output_data={
                "total_proyecto": salida_costos.total_proyecto,
                "items_costos": len(salida_costos.df_costos_materiales)
                if salida_costos.df_costos_materiales is not None else 0,
            },
            estado={
                "ok": salida_costos.ok,
                "errores": salida_costos.errores,
                "warnings": salida_costos.warnings,
            }
        )

        if not salida_costos.ok:
            return ResultadoProyecto(
                ok=False,
                errores=salida_costos.errores,
                warnings=salida_costos.warnings,
                materiales=salida_materiales,
                costos=salida_costos,
                debug=debug_global,
            )

        # =====================================================
        # 🔷 4. REPORTES
        # =====================================================
        salida_reportes = generar_reportes(
            materiales=salida_materiales,
            costos=salida_costos,
        )

        debug_global["reportes"] = {
            "etapa": "reportes",
            "estado": {
                "ok": True,
                "archivos_generados": list(salida_reportes.keys())
                if isinstance(salida_reportes, dict) else [],
            }
        }

        # =====================================================
        # RESULTADO FINAL
        # =====================================================
        return ResultadoProyecto(
            ok=True,
            errores=[],
            warnings=[],
            materiales=salida_materiales,
            costos=salida_costos,
            reportes=salida_reportes,
            debug=debug_global,
        )

    except Exception as e:
        return ResultadoProyecto(
            ok=False,
            errores=[str(e), traceback.format_exc()],
            warnings=[],
            debug=debug_global,
        )
