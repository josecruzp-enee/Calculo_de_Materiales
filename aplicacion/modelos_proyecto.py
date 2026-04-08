# -*- coding: utf-8 -*-
from __future__ import annotations

from materiales.orquestador_materiales import ejecutar_materiales
from costos_precios.orquestador_costos import ejecutar_costos

from aplicacion.modelos_proyecto import EntradaProyecto
from materiales.modelos.entrada import EntradaMateriales


def ejecutar_proyecto(entrada: EntradaProyecto):

    # =====================================================
    # 0. VALIDACIÓN CENTRAL
    # =====================================================
    entrada.validar_costos()

    # =====================================================
    # 1. ADAPTADOR → MATERIALES
    # =====================================================
    entrada_materiales = EntradaMateriales(
        estructuras_df=entrada.df_estructuras,
        tension=entrada.tension,
        datos_proyecto=entrada.datos_proyecto,
        df_cables=entrada.df_cables,
        df_materiales_extra=entrada.df_materiales_extra,
    )

    # =====================================================
    # 2. MATERIALES
    # =====================================================
    salida_materiales = ejecutar_materiales(entrada_materiales)

    if not salida_materiales.ok:
        return {
            "ok": False,
            "fase": "materiales",
            "errores": salida_materiales.errores,
        }

    # =====================================================
    # 3. COSTOS
    # =====================================================
    salida_costos = None

    if entrada.calcular_costos:

        salida_costos = ejecutar_costos({
            "df_resumen": salida_materiales.df_materiales,
            "df_estructuras": salida_materiales.df_estructuras,
            "df_estructuras_por_punto": salida_materiales.df_estructuras_por_punto,

            # 🔹 fuente precios
            "df_precios_materiales": entrada.df_precios_materiales,
            "ruta_materiales": entrada.ruta_materiales,

            # 🔹 override
            "df_costos_estructuras": entrada.df_costos_estructuras,

            # 🔹 parámetros operativos
            "costo_cuadrilla_dia": entrada.costo_cuadrilla_dia,
            "fraccion_jornada": entrada.fraccion_jornada,
            "costo_equipos": entrada.costo_equipos,
            "costo_logistica": entrada.costo_logistica,
            "margen_utilidad": entrada.margen_utilidad,
        })

    # =====================================================
    # 4. OUTPUT
    # =====================================================
    return {
        "ok": True,

        "materiales": salida_materiales,
        "costos": salida_costos,

        # 🔹 acceso rápido
        "df_materiales": salida_materiales.df_materiales,
        "df_materiales_por_punto": salida_materiales.df_materiales_por_punto,
        "df_estructuras": salida_materiales.df_estructuras,
        "df_estructuras_por_punto": salida_materiales.df_estructuras_por_punto,
    }
