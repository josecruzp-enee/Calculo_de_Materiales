# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Any
import pandas as pd

# =========================================================
# CONTRATO (ÚNICO)
# =========================================================
from aplicacion.modelos_proyecto import EntradaProyecto

# =========================================================
# DOMINIOS
# =========================================================
from materiales.modelos.entrada import EntradaMateriales
from materiales.orquestador_materiales import ejecutar_materiales

from costos_precios.orquestador_costos import ejecutar_costos
from costos_precios.costos_estructuras import calcular_costos_por_estructura
from entradas.base_datos import cargar_base_datos

base_datos = cargar_base_datos(entrada.ruta_materiales)

# =========================================================
# HELPERS
# =========================================================
def _conteo_estructuras(df: pd.DataFrame) -> Dict[str, float]:
    if df is None or df.empty:
        return {}

    df = df.copy()
    cols = {c.strip().lower(): c for c in df.columns}

    col_est = cols.get("estructura") or cols.get("codigodeestructura")
    col_cant = cols.get("cantidad")

    if not col_est or not col_cant:
        raise ValueError(
            f"Columnas requeridas no encontradas en estructuras: {list(df.columns)}"
        )

    df[col_est] = df[col_est].astype(str).str.strip().str.upper()
    df[col_cant] = pd.to_numeric(df[col_cant], errors="coerce").fillna(0)

    return dict(zip(df[col_est], df[col_cant]))


# =========================================================
# ORQUESTADOR PRINCIPAL
# =========================================================
def ejecutar_proyecto(entrada: EntradaProyecto) -> Dict[str, Any]:

    # =========================================
    # VALIDACIÓN FUERTE
    # =========================================
    if not isinstance(entrada, EntradaProyecto):
        raise TypeError("entrada debe ser EntradaProyecto")

    entrada.validar()

    if entrada.tension is None:
        raise ValueError("tension es requerida")

    # =========================================
    # 1. MATERIALES
    # =========================================
    entrada_mat = EntradaMateriales(
        estructuras_df=entrada.df_estructuras,
        tension=entrada.tension,
        datos_proyecto=entrada.datos_proyecto,
        df_cables=getattr(entrada, "df_cables", None),
        df_materiales_extra=getattr(entrada, "df_materiales_extra", None),
        calibre_mt=entrada.calibre_mt,
        tabla_conectores_mt=entrada.tabla_conectores_mt,
    )

    salida_materiales = ejecutar_materiales(entrada_mat)

    if (
        salida_materiales is None
        or salida_materiales.df_materiales is None
        or salida_materiales.df_materiales.empty
    ):
        raise ValueError("Error en cálculo de materiales")

    # =========================================
    # 2. COSTOS POR ESTRUCTURA
    # =========================================
    df_costos_estructuras = entrada.df_costos_estructuras

    if df_costos_estructuras is None or df_costos_estructuras.empty:

        conteo = _conteo_estructuras(entrada.df_estructuras)

        hojas_base = getattr(entrada, "hojas_base", {})

        df_costos_estructuras = calcular_costos_por_estructura(
            hojas_base=hojas_base,
            conteo=conteo,
            tension_ll=entrada.tension,
            calibre_mt=entrada.calibre_mt,
            tabla_conectores_mt=entrada.tabla_conectores_mt,
            df_precios_materiales=entrada.df_precios_materiales,
        )

    # =========================================
    # 3. COSTOS
    # =========================================
    salida_costos = ejecutar_costos({
        "df_resumen": salida_materiales.df_materiales,
        "df_estructuras_por_punto": salida_materiales.df_estructuras_por_punto,
        "df_costos_estructuras": df_costos_estructuras,
        "df_precios_materiales": entrada.df_precios_materiales,
    })

    # =========================================
    # 4. OUTPUT NORMALIZADO (CLAVE 🔥)
    # =========================================
    resultado = {
        "ok": True,

        # 🔹 materiales
        "materiales": salida_materiales,
        "df_materiales": salida_materiales.df_materiales,
        "df_por_punto": salida_materiales.df_materiales_por_punto,

        # 🔹 estructuras
        "df_estructuras": salida_materiales.df_estructuras,

        # 🔹 costos (formato esperado por reportes)
        "costos": salida_costos,

        # 🔹 resumen (alias para excel/reportes)
        "df_resumen": salida_materiales.df_materiales,

        # 🔹 metadata
        "nombre_proyecto": (
            entrada.datos_proyecto.get("nombre")
            if entrada.datos_proyecto else "Proyecto"
        ),
    }

    return resultado
