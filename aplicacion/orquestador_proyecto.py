# -*- coding: utf-8 -*-
# aplicacion/orquestador_proyecto.py

from __future__ import annotations

import pandas as pd

from aplicacion.modelos_proyecto import EntradaProyecto

# =========================
# CONTRATOS
# =========================
from interfaz.contratos import ResultadoProyecto, SalidaMateriales

# =========================
# DOMINIO
# =========================
from materiales.orquestador_materiales import ejecutar_materiales
from materiales.modelos.entrada import EntradaMateriales

# =========================
# BASE
# =========================
from entradas.base_datos import cargar_base_datos, obtener_catalogo_materiales


# =========================================================
# ORQUESTADOR PRINCIPAL
# =========================================================
def ejecutar_proyecto(entrada_proyecto: EntradaProyecto) -> ResultadoProyecto:

    debug = {}

    # =====================================================
    # 1. VALIDACIÓN
    # =====================================================
    errores = _validar_entrada(entrada_proyecto)
    if errores:
        return ResultadoProyecto(
            ok=False,
            errores=errores,
            debug={"fase": "validacion"}
        )

    # =====================================================
    # 2. NORMALIZACIÓN
    # =====================================================
    df_cables, df_materiales_extra = _normalizar_opcionales(entrada_proyecto)

    # =====================================================
    # 3. BASE DE DATOS
    # =====================================================
    base, catalogo, error_base = _cargar_base()
    if error_base:
        return ResultadoProyecto(
            ok=False,
            errores=[error_base],
            debug={"fase": "base_datos"}
        )

    # =====================================================
    # 4. BUILDER
    # =====================================================
    entrada_materiales, error_builder = _construir_entrada_materiales(
        entrada_proyecto,
        base,
        df_cables,
        df_materiales_extra
    )

    if error_builder:
        return ResultadoProyecto(
            ok=False,
            errores=[error_builder],
            debug={"fase": "builder"}
        )

    # =====================================================
    # 5. EJECUCIÓN MATERIALES
    # =====================================================
    salida_materiales, error_calculo = _ejecutar_materiales_safe(
        entrada_materiales,
        catalogo
    )

    if error_calculo:
        return ResultadoProyecto(
            ok=False,
            errores=[error_calculo],
            debug={"fase": "calculo"}
        )

    # =====================================================
    # 6. CONSOLIDACIÓN FINAL
    # =====================================================
    debug["materiales"] = salida_materiales.debug

    return ResultadoProyecto(
        ok=salida_materiales.ok,
        errores=salida_materiales.errores,
        warnings=salida_materiales.warnings,
        materiales=salida_materiales,
        datos_proyecto=entrada_proyecto.__dict__,
        debug=debug
    )


# =========================================================
# VALIDACIÓN
# =========================================================
def _validar_entrada(entrada: EntradaProyecto) -> list[str]:

    errores = []

    if entrada is None:
        return ["EntradaProyecto es None"]

    if entrada.df_estructuras is None or entrada.df_estructuras.empty:
        errores.append("No hay estructuras")

    if not entrada.ruta_materiales:
        errores.append("Ruta de materiales no definida")

    return errores


# =========================================================
# NORMALIZACIÓN
# =========================================================
def _normalizar_opcionales(entrada: EntradaProyecto):

    df_cables = entrada.df_cables
    if df_cables is not None and not hasattr(df_cables, "empty"):
        df_cables = None

    df_materiales_extra = entrada.df_materiales_extra
    if df_materiales_extra is not None and not hasattr(df_materiales_extra, "empty"):
        df_materiales_extra = None

    return df_cables, df_materiales_extra


# =========================================================
# BASE
# =========================================================
def _cargar_base():

    try:
        base = cargar_base_datos()
        catalogo = obtener_catalogo_materiales(base)
        return base, catalogo, None
    except Exception as e:
        return None, None, str(e)


# =========================================================
# BUILDER
# =========================================================
def _construir_entrada_materiales(
    entrada_proyecto: EntradaProyecto,
    base,
    df_cables,
    df_materiales_extra
):

    try:
        tension = getattr(entrada_proyecto, "tension", None) or 34.5

        entrada = EntradaMateriales(
            estructuras_df=entrada_proyecto.df_estructuras,
            tension=tension,
            hojas_base=base,
            df_cables=df_cables,
            df_materiales_extra=df_materiales_extra,
        )

        return entrada, None

    except Exception as e:
        return None, str(e)


# =========================================================
# EJECUCIÓN SEGURA
# =========================================================
def _ejecutar_materiales_safe(entrada, catalogo):

    try:
        resultado = ejecutar_materiales(
            entrada,
            catalogo=catalogo
        )
        return resultado, None

    except Exception as e:
        return None, str(e)
