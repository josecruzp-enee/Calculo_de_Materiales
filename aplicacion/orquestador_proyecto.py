# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Any

# =====================================================
# ORQUESTADORES
# =====================================================
from materiales.orquestador_materiales import ejecutar_materiales
from costos_precios.orquestador_costos import ejecutar_costos

# =====================================================
# CONTRATOS
# =====================================================
from materiales.modelos.entrada import EntradaMateriales


def ejecutar_proyecto(data: Dict[str, Any]) -> Dict[str, Any]:

    if not isinstance(data, dict):
        raise TypeError("data debe ser dict")

    # =====================================================
    # 1. ADAPTAR INPUT → MODELO FUERTE
    # =====================================================
    entrada_materiales = EntradaMateriales(
        estructuras_df=data.get("df_estructuras"),
        tension=data.get("tension"),
        datos_proyecto=data.get("datos_proyecto"),
        df_cables=data.get("df_cables"),
        df_materiales_extra=data.get("df_materiales_extra"),
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
    # 3. COSTOS (🔥 SOLO ORQUESTADOR)
    # =====================================================
    salida_costos = ejecutar_costos({
        "df_resumen": salida_materiales.df_materiales,
        "df_estructuras_por_punto": salida_materiales.df_estructuras_por_punto,
        "df_estructuras": salida_materiales.df_estructuras,
        "datos_proyecto": data.get("datos_proyecto"),
        "archivo_precios_materiales": data.get("archivo_materiales"),
    })

    # =====================================================
    # 4. OUTPUT FINAL LIMPIO
    # =====================================================
    return {
        "ok": True,

        "materiales": salida_materiales,
        "costos": salida_costos,

        # 🔹 acceso rápido (para reportes)
        "df_materiales": salida_materiales.df_materiales,
        "df_materiales_por_punto": salida_materiales.df_materiales_por_punto,
        "df_estructuras": salida_materiales.df_estructuras,
        "df_estructuras_por_punto": salida_materiales.df_estructuras_por_punto,
    }
