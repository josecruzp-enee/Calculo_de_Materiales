# -*- coding: utf-8 -*-
# materiales/orquestador_materiales.py

from __future__ import annotations

import pandas as pd

from materiales.modelos.entrada import EntradaMateriales
from materiales.modelos.salida import ResultadoMateriales

from entradas.normalizar import normalizar_estructuras

from materiales.calculos.calculo_materiales import (
    calcular_materiales_proyecto,
)

from materiales.validaciones.materiales_validacion import (
    validar_datos_proyecto,
)


# ==========================================================
# ORQUESTADOR PRINCIPAL
# ==========================================================
def ejecutar_materiales(
    *,
    df_estructuras: pd.DataFrame,
    tension: float,
    df_cables: pd.DataFrame | None = None,
    datos_proyecto: dict | None = None,
    hojas_base: dict[str, pd.DataFrame] | None = None,
) -> ResultadoMateriales:

    errores: list[str] = []
    warnings: list[str] = []

    # ======================================================
    # 1. VALIDACIÓN ENTRADAS
    # ======================================================
    if df_estructuras is None or df_estructuras.empty:
        return ResultadoMateriales(
            ok=False,
            errores=["df_estructuras vacío"],
            warnings=[],
        )

    try:
        tension = float(tension)
    except Exception:
        return ResultadoMateriales(
            ok=False,
            errores=[f"Tensión inválida: {tension}"],
            warnings=[],
        )

    # Validación opcional de datos de proyecto
    if datos_proyecto:
        err_val, warn_val = validar_datos_proyecto(datos_proyecto)
        errores.extend(err_val or [])
        warnings.extend(warn_val or [])

    # ======================================================
    # 2. NORMALIZACIÓN
    # ======================================================
    try:
        df_norm, err_norm, warn_norm = normalizar_estructuras(df_estructuras)
        errores.extend(err_norm or [])
        warnings.extend(warn_norm or [])
    except Exception as e:
        return ResultadoMateriales(
            ok=False,
            errores=[f"Error en normalización: {e}"],
            warnings=warnings,
        )

    if df_norm is None or df_norm.empty:
        return ResultadoMateriales(
            ok=False,
            errores=["Normalización produjo vacío"],
            warnings=warnings,
        )

    # ======================================================
    # 3. CONSTRUIR DTO
    # ======================================================
    entrada = EntradaMateriales(
        estructuras_df=df_norm,
        tension=tension,
        df_cables=df_cables,
        datos_proyecto=datos_proyecto,
        hojas_base=hojas_base,
    )

    # ======================================================
    # 4. CÁLCULO
    # ======================================================
    try:
        resultado_calc = calcular_materiales_proyecto(entrada)
    except Exception as e:
        return ResultadoMateriales(
            ok=False,
            errores=[f"Error en cálculo: {e}"],
            warnings=warnings,
        )

    # ======================================================
    # 5. CONSOLIDACIÓN
    # ======================================================
    df_materiales = resultado_calc.get("df_materiales")
    df_detalle = resultado_calc.get("df_detalle")
    conteo = resultado_calc.get("conteo_estructuras")

    if df_materiales is None or df_materiales.empty:
        errores.append("No se generaron materiales")

    # ======================================================
    # 6. SALIDA
    # ======================================================
    return ResultadoMateriales(
        ok=len(errores) == 0,
        errores=errores,
        warnings=warnings,
        df_materiales=df_materiales,
        df_detalle=df_detalle,
        conteo_estructuras=conteo,
    )
