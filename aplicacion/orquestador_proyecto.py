# -*- coding: utf-8 -*-
from __future__ import annotations

# =====================================================
# ORQUESTADORES
# =====================================================
from materiales.orquestador_materiales import ejecutar_materiales
from costos_precios.orquestador_costos import ejecutar_costos

# =====================================================
# CONTRATOS
# =====================================================
from materiales.modelos.entrada import EntradaMateriales
from interfaz.contratos import SalidaInterfaz


def ejecutar_proyecto(entrada: SalidaInterfaz):

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    if not isinstance(entrada, SalidaInterfaz):
        raise TypeError("entrada debe ser SalidaInterfaz")

    if not entrada.ok:
        return {
            "ok": False,
            "error": "Error en interfaz",
            "detalle": entrada.errores,
        }

    # =====================================================
    # 1. ADAPTAR INPUT → MODELO FUERTE
    # =====================================================
    entrada_materiales = EntradaMateriales(
        estructuras_df=entrada.data_entrada,
        tension=entrada.datos_proyecto.get("tension"),
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
            "error": "Error en materiales",
            "detalle": salida_materiales.errores,
        }

    # =====================================================
    # 3. COSTOS (se mantiene dict por compatibilidad)
    # =====================================================
    salida_costos = ejecutar_costos({
        "df_resumen": salida_materiales.df_materiales,
        "df_estructuras_por_punto": salida_materiales.df_estructuras_por_punto,
        "df_estructuras": salida_materiales.df_estructuras,
        "datos_proyecto": entrada.datos_proyecto,
        "archivo_precios_materiales": None,  # ajusta si usas archivo real
    })

    # =====================================================
    # 4. OUTPUT FINAL
    # =====================================================
    return {
        "ok": True,

        "materiales": salida_materiales,
        "costos": salida_costos,

        # 🔹 accesos rápidos (para reportes/UI)
        "df_materiales": salida_materiales.df_materiales,
        "df_materiales_por_punto": salida_materiales.df_materiales_por_punto,
        "df_estructuras": salida_materiales.df_estructuras,
        "df_estructuras_por_punto": salida_materiales.df_estructuras_por_punto,
    }
