# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import pandas as pd

# =====================================================
# ORQUESTADORES
# =====================================================
from materiales.orquestador_materiales import ejecutar_materiales
from costos_precios.orquestador_costos import ejecutar_costos
from costos_precios.costos_estructuras import calcular_costos_por_estructura

# =====================================================
# INFRAESTRUCTURA
# =====================================================
from entradas.base_datos import cargar_base_datos

# =====================================================
# CONTRATOS
# =====================================================
from materiales.modelos.entrada import EntradaMateriales
from aplicacion.modelos_proyecto import EntradaProyecto


# =====================================================
# HELPERS
# =====================================================
def _conteo_estructuras(df_estructuras):
    if df_estructuras is None or df_estructuras.empty:
        return {}

    df = df_estructuras.copy()
    df["Estructura"] = df["Estructura"].astype(str).str.strip().str.upper()
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)

    return dict(zip(df["Estructura"], df["Cantidad"]))


# =====================================================
# ORQUESTADOR PRINCIPAL
# =====================================================
def ejecutar_proyecto(entrada: EntradaProyecto):

    # =====================================================
    # VALIDACIÓN INPUT
    # =====================================================
    if not isinstance(entrada, EntradaProyecto):
        raise TypeError("entrada debe ser EntradaProyecto")

    entrada.validar()

    # =====================================================
    # 1. MATERIALES
    # =====================================================
    entrada_materiales = EntradaMateriales(
        estructuras_df=entrada.df_estructuras,
        tension=entrada.tension,
        datos_proyecto=entrada.datos_proyecto,
        df_cables=entrada.df_cables,
        df_materiales_extra=entrada.df_materiales_extra,
    )

    salida_materiales = ejecutar_materiales(entrada_materiales)

    if not salida_materiales.ok:
        return {
            "ok": False,
            "error": "Error en materiales",
            "detalle": salida_materiales.errores,
        }

    # =====================================================
    # 2. COSTOS
    # =====================================================
    salida_costos = None

    if entrada.calcular_costos:

        if entrada.ruta_materiales is None:
            raise ValueError("Falta ruta_materiales para costos")

        ruta = Path(entrada.ruta_materiales)

        # 🔹 base de datos
        hojas_base = cargar_base_datos(ruta)

        # 🔹 conteo correcto (GLOBAL)
        conteo = _conteo_estructuras(salida_materiales.df_estructuras)

        # 🔹 costos por estructura
        df_costos_estructuras = calcular_costos_por_estructura(
            hojas_base=hojas_base,
            conteo=conteo,
            tension_ll=entrada.tension,
            calibre_mt=entrada.calibre_mt,
            tabla_conectores_mt=entrada.tabla_conectores_mt,
            df_precios_materiales=entrada.df_precios_materiales,
        )

        # 🔹 costos finales
        salida_costos = ejecutar_costos({
            "df_resumen": salida_materiales.df_materiales,
            "df_estructuras_por_punto": salida_materiales.df_estructuras_por_punto,
            "df_costos_estructuras": df_costos_estructuras,
            "df_precios_materiales": entrada.df_precios_materiales,
            "archivo_precios_materiales": str(ruta),
        })

    # =====================================================
    # 3. OUTPUT FINAL
    # =====================================================
    return {
        "ok": True,
        "materiales": salida_materiales,
        "costos": salida_costos,

        # accesos rápidos
        "df_materiales": salida_materiales.df_materiales,
        "df_materiales_por_punto": salida_materiales.df_materiales_por_punto,
        "df_estructuras": salida_materiales.df_estructuras,
        "df_estructuras_por_punto": salida_materiales.df_estructuras_por_punto,
    }
