# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Any

from aplicacion.modelos_proyecto import EntradaProyecto

from materiales.modelos.entrada import EntradaMateriales
from materiales.orquestador_materiales import ejecutar_materiales

from costos_precios.orquestador_costos import ejecutar_costos


def ejecutar_proyecto(entrada: EntradaProyecto) -> Dict[str, Any]:

    # =========================================
    # VALIDACIÓN FUERTE
    # =========================================
    if not isinstance(entrada, EntradaProyecto):
        raise TypeError("entrada debe ser EntradaProyecto")

    entrada.validar()

    # =========================================
    # 1. MATERIALES (DOMINIO)
    # =========================================
    entrada_mat = EntradaMateriales(
        estructuras_df=entrada.df_estructuras,
        ruta_base=entrada.ruta_materiales,
        datos_proyecto={
            "tension": entrada.tension,
            "calibre_mt": entrada.calibre_mt,
        },
    )

    salida_materiales = ejecutar_materiales(entrada_mat)

    if (
        salida_materiales is None
        or salida_materiales.df_materiales is None
        or salida_materiales.df_materiales.empty
    ):
        raise ValueError("Error en cálculo de materiales")

    # =========================================
    # 2. COSTOS (DOMINIO)
    # =========================================
    try:
        salida_costos = ejecutar_costos({
            "df_resumen": salida_materiales.df_materiales,
            "df_estructuras_por_punto": getattr(
                salida_materiales, "df_estructuras_por_punto", None
            ),
            "df_costos_estructuras": entrada.df_costos_estructuras,
            "df_precios_materiales": entrada.df_precios_materiales,
        })
    except Exception as e:
        raise ValueError(f"Error en cálculo de costos: {str(e)}")

    # =========================================
    # 3. OUTPUT LIMPIO
    # =========================================
    return {
        "materiales": salida_materiales,
        "costos": salida_costos,
    }
