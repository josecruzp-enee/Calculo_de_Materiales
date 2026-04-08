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
    # 1. INPUT
    # =====================================================
    _debug("INPUT", "entrada_proyecto", entrada_proyecto)

    # =====================================================
    # 2. VALIDACIÓN
    # =====================================================
    errores = _validar_entrada(entrada_proyecto)

    _debug("VALIDACION", "errores", errores)
    _check("VALIDACION", "sin_errores", not errores, errores)

    if errores:
        return ResultadoProyecto(
            ok=False,
            errores=errores,
            debug={"fase": "validacion"}
        )

    # =====================================================
    # 3. NORMALIZACIÓN OPCIONALES
    # =====================================================
    df_cables, df_materiales_extra = _normalizar_opcionales(entrada_proyecto)

    _debug("NORMALIZACION", "df_cables", df_cables)
    _debug("NORMALIZACION", "df_materiales_extra", df_materiales_extra)

    # =====================================================
    # 4. BASE DE DATOS
    # =====================================================
    base, catalogo, error_base = _cargar_base()

    _debug("BASE", "base_keys", list(base.keys())[:10] if isinstance(base, dict) else None)
    _debug("BASE", "catalogo", type(catalogo).__name__)

    _check("BASE", "base_ok", base is not None)
    _check("BASE", "catalogo_ok", catalogo is not None)

    if error_base:
        return ResultadoProyecto(
            ok=False,
            errores=[error_base],
            debug={"fase": "base_datos"}
        )

    # =====================================================
    # 5. BUILDER
    # =====================================================
    entrada_materiales, error_builder = _construir_entrada_materiales(
        entrada_proyecto,
        base,
        df_cables,
        df_materiales_extra
    )

    _debug("BUILDER", "entrada_materiales", entrada_materiales)
    _check("BUILDER", "builder_ok", entrada_materiales is not None)

    if error_builder:
        return ResultadoProyecto(
            ok=False,
            errores=[error_builder],
            debug={"fase": "builder"}
        )

    # =====================================================
    # 6. EJECUCIÓN MATERIALES
    # =====================================================
    salida_materiales, error_calculo = _ejecutar_materiales_safe(
        entrada_materiales,
        catalogo
    )

    _debug("CALCULO", "salida_materiales", salida_materiales)
    _check("CALCULO", "salida_ok", salida_materiales is not None)

    if error_calculo:
        return ResultadoProyecto(
            ok=False,
            errores=[error_calculo],
            debug={"fase": "calculo"}
        )

    # =====================================================
    # 7. OUTPUT FINAL
    # =====================================================
    debug["pipeline"] = {
        "ok": salida_materiales.ok,
        "errores": salida_materiales.errores,
        "warnings": salida_materiales.warnings,
    }

    debug["materiales"] = salida_materiales.debug

    _debug("OUTPUT", "resultado_final_ok", salida_materiales.ok)

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
        tension = getattr(entrada_proyecto, "tension", None)

        if tension is None:
            raise ValueError("Tensión no definida")

        tension = float(tension)

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
