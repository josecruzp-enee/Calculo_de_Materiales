# -*- coding: utf-8 -*-
from __future__ import annotations

# =====================================================
# ORQUESTADORES
# =====================================================
from materiales.orquestador_materiales import ejecutar_materiales
from costos_precios.orquestador_costos import ejecutar_costos
from entradas.orquestador_entradas import ejecutar_entradas

# =====================================================
# CONTRATOS
# =====================================================
from materiales.modelos.entrada import EntradaMateriales
from interfaz.contratos import SalidaInterfaz


def ejecutar_proyecto(entrada: SalidaInterfaz):

    if not isinstance(entrada, SalidaInterfaz):
        raise TypeError("entrada debe ser SalidaInterfaz")

    if not entrada.ok:
        return {
            "ok": False,
            "error": "Error en interfaz",
            "detalle": entrada.errores,
        }

    # =====================================================
    # ENTRADAS
    # =====================================================
    salida_entradas = ejecutar_entradas(entrada)

    if not salida_entradas.ok:
        return {
            "ok": False,
            "error": "Error en entradas",
            "detalle": salida_entradas.errores,
        }

    # =====================================================
    # MATERIALES
    # =====================================================
    entrada_materiales = EntradaMateriales(
        estructuras_df=salida_entradas.df_estructuras,
        tension=salida_entradas.datos_proyecto.get("tension"),
        datos_proyecto=salida_entradas.datos_proyecto,
        df_cables=salida_entradas.df_cables,
        df_materiales_extra=salida_entradas.df_materiales_extra,
    )

    salida_materiales = ejecutar_materiales(entrada_materiales)

    if not salida_materiales.ok:
        return {
            "ok": False,
            "error": "Error en materiales",
            "detalle": salida_materiales.errores,
        }

    # =====================================================
    # COSTOS
    # =====================================================
    salida_costos = ejecutar_costos({
        "df_resumen": salida_materiales.df_materiales,
        "df_estructuras_por_punto": salida_materiales.df_estructuras_por_punto,
        "df_estructuras": salida_materiales.df_estructuras,
        "datos_proyecto": salida_entradas.datos_proyecto,
        "archivo_precios_materiales": None,
    })

    # =====================================================
    # OUTPUT
    # =====================================================
    return {
        "ok": True,
        "materiales": salida_materiales,
        "costos": salida_costos,
        "df_materiales": salida_materiales.df_materiales,
        "df_materiales_por_punto": salida_materiales.df_materiales_por_punto,
        "df_estructuras": salida_materiales.df_estructuras,
        "df_estructuras_por_punto": salida_materiales.df_estructuras_por_punto,
    }
