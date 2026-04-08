# -*- coding: utf-8 -*-
# aplicacion/orquestador_proyecto.py

from __future__ import annotations

import pandas as pd
import streamlit as st

from aplicacion.modelos_proyecto import EntradaProyecto

# =========================
# CONTRATOS
# =========================
from interfaz.contratos import ResultadoProyecto

# =========================
# DOMINIO
# =========================
from materiales.orquestador_materiales import ejecutar_materiales
from materiales.modelos.entrada import EntradaMateriales

# 🔥 COSTOS
from costos_precios.orquestador_costos import ejecutar_costos
from costos_precios.costos_estructuras import calcular_costos_por_estructura

# =========================
# BASE
# =========================
from entradas.base_datos import cargar_base_datos, obtener_catalogo_materiales

# =========================
# DEBUG
# =========================
from ayuda.debug import debug_guardar


def _debug(etapa, nombre, valor):
    debug_guardar(f"PROYECTO::{etapa}::{nombre}", valor)


def _check(etapa, nombre, condicion, detalle=None):
    debug_guardar(f"CHECK::PROYECTO::{etapa}::{nombre}", {
        "ok": bool(condicion),
        "detalle": str(detalle)[:200]
    })


# =========================================================
# ORQUESTADOR PRINCIPAL
# =========================================================
def ejecutar_proyecto(entrada_proyecto: EntradaProyecto) -> ResultadoProyecto:

    debug = {}

    # =====================================================
    # 1. VALIDACIÓN
    # =====================================================
    try:
        entrada_proyecto.validar_costos()
    except Exception as e:
        return ResultadoProyecto(
            ok=False,
            errores=[str(e)],
            debug={"fase": "validacion_costos"}
        )

    errores = _validar_entrada(entrada_proyecto)

    if errores:
        return ResultadoProyecto(
            ok=False,
            errores=errores,
            debug={"fase": "validacion"}
        )

    # =====================================================
    # 2. NORMALIZACIÓN OPCIONALES
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
            debug={"fase": "calculo_materiales"}
        )

    # =====================================================
    # 6. COSTOS POR ESTRUCTURA
    # =====================================================
    try:

        # 🔹 usar override si viene
        if entrada_proyecto.df_costos_estructuras is not None:
            df_costos_estructuras = entrada_proyecto.df_costos_estructuras

        else:
            df_costos_estructuras = calcular_costos_por_estructura(
                archivo_materiales=entrada_proyecto.ruta_materiales,
                conteo=salida_materiales.conteo_estructuras,
                tension_ll=entrada_proyecto.tension,
                calibre_mt=salida_materiales.calibre_mt,
                tabla_conectores_mt=salida_materiales.tabla_conectores_mt,

                # 🔥 parámetros operativos
                costo_cuadrilla_dia=entrada_proyecto.costo_cuadrilla_dia,
                fraccion_jornada=entrada_proyecto.fraccion_jornada,
                costo_equipos=entrada_proyecto.costo_equipos,
                costo_logistica=entrada_proyecto.costo_logistica,
                margen_utilidad=entrada_proyecto.margen_utilidad,
            )

    except Exception as e:
        return ResultadoProyecto(
            ok=False,
            errores=[f"Error en costos por estructura: {str(e)}"],
            debug={"fase": "costos_estructura"}
        )

    # =====================================================
    # 7. COSTOS POR PUNTO
    # =====================================================
    try:

        costos = ejecutar_costos({
            "df_resumen": salida_materiales.df_materiales,
            "df_estructuras_por_punto": salida_materiales.df_estructuras_por_punto,
            "df_costos_estructuras": df_costos_estructuras,
            "archivo_precios_materiales": entrada_proyecto.ruta_materiales,
        })

    except Exception as e:
        return ResultadoProyecto(
            ok=False,
            errores=[f"Error en costos por punto: {str(e)}"],
            debug={"fase": "costos_punto"}
        )

    # =====================================================
    # 8. OUTPUT FINAL
    # =====================================================
    debug["costos"] = list(costos.keys())

    return ResultadoProyecto(
        ok=True,
        errores=[],
        warnings=[],
        materiales=salida_materiales,

        # 🔥 COSTOS COMPLETOS
        costos=costos,

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

    if entrada.tension is None:
        errores.append("Tensión no definida")

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

        st.session_state["hojas_base"] = base

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
        tension = float(entrada_proyecto.tension)

        df = entrada_proyecto.df_estructuras

        if df is None or df.empty:
            raise ValueError("df_estructuras vacío")

        if "codigodeestructura" not in df.columns:
            raise ValueError("Falta columna codigodeestructura")

        return EntradaMateriales(
            estructuras_df=df.copy(),
            tension=tension,
            datos_proyecto=entrada_proyecto.datos_proyecto,
            df_cables=df_cables,
            df_materiales_extra=df_materiales_extra,
        ), None

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
