# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional
import pandas as pd
import traceback
import streamlit as st

# =========================================================
# 📦 CONTRATO
# =========================================================
@dataclass(slots=True)
class EntradaReportes:
    df_estructuras: pd.DataFrame
    df_materiales: pd.DataFrame
    df_materiales_por_punto: pd.DataFrame

    costos: Optional[Dict[str, Any]] = None

    nombre_proyecto: str = "Proyecto"


# =========================================================
# 📄 IMPORTS
# =========================================================
from exportadores.pdf_reportes_simples import (
    generar_pdf_estructuras_global,
    generar_pdf_estructuras_por_punto,
    generar_pdf_materiales,
    generar_pdf_materiales_por_punto,
)

from exportadores.pdf_completo import generar_pdf_completo

from exportadores.pdf_anexos_costos import (
    tabla_costos_materiales_pdf,
    tabla_costos_estructuras_pdf,
    tabla_costos_por_punto_pdf,
)

from exportadores.excel_utils import exportar_excel

# 🔥 CLAVE
from costos_precios.precio_por_estructura import calcular_precios_por_estructura


# =========================================================
# 🧩 HELPERS
# =========================================================
def _fail(msg: str, debug: Optional[dict] = None):
    return {
        "archivos": {},
        "errores": [msg],
        "debug": debug or {},
    }


def _safe_exec(nombre, fn):
    try:
        return fn(), None
    except Exception as e:
        return None, f"{nombre}: {str(e)}\n{traceback.format_exc()}"


def _add_file(archivos, errores, nombre, contenido):
    if isinstance(contenido, (bytes, bytearray)):
        archivos[nombre] = contenido
    else:
        errores.append(f"{nombre} inválido")


def _validar_df(df, nombre, columnas=None):
    if df is None or not isinstance(df, pd.DataFrame):
        raise ValueError(f"{nombre} inválido")

    if df.empty:
        raise ValueError(f"{nombre} vacío")

    if columnas:
        faltantes = [c for c in columnas if c not in df.columns]
        if faltantes:
            raise ValueError(f"{nombre} sin columnas: {faltantes}")


# =========================================================
# 🚀 ORQUESTADOR
# =========================================================
def generar_reportes(entrada: EntradaReportes) -> Dict[str, Any]:

    try:
        _validar_df(entrada.df_estructuras, "df_estructuras")
        _validar_df(entrada.df_materiales, "df_materiales")
        _validar_df(entrada.df_materiales_por_punto, "df_materiales_por_punto")

        costos = entrada.costos or {}

        df_costos_estructuras = costos.get("df_costos_estructura")
        df_costos_por_punto = costos.get("df_costos_por_punto")

        archivos = {}
        errores = []
        debug = {}

        nombre = entrada.nombre_proyecto

        # =====================================================
        # 📊 DATOS PROYECTO
        # =====================================================
        datos_proyecto = st.session_state.get("datos_proyecto", {})

        # =====================================================
        # 🔥 CALCULAR PRECIOS (AQUÍ ESTABA EL PROBLEMA)
        # =====================================================
        df_precios_estructura = None

        if df_costos_estructuras is not None and not df_costos_estructuras.empty:
            try:
                df_precios_estructura, _ = calcular_precios_por_estructura(
                    df_costos_estructuras,
                    entrada.df_estructuras,
                )
            except Exception as e:
                st.write("❌ ERROR CALCULANDO PRECIOS:", e)

        # =====================================================
        # 📄 TASKS
        # =====================================================
        tasks = [

            ("estructuras_global.pdf", lambda: generar_pdf_estructuras_global(
                entrada.df_estructuras, nombre
            )),

            ("estructuras_por_punto.pdf", lambda: generar_pdf_estructuras_por_punto(
                entrada.df_estructuras, nombre
            )),

            ("materiales.pdf", lambda: generar_pdf_materiales(
                entrada.df_materiales, nombre
            )),

            ("materiales_por_punto.pdf", lambda: generar_pdf_materiales_por_punto(
                entrada.df_materiales_por_punto, nombre
            )),

            # 🔥 ESTE ES EL IMPORTANTE
            ("reporte_completo.pdf", lambda: generar_pdf_completo(
                df_materiales=entrada.df_materiales,
                df_estructuras=entrada.df_estructuras,
                df_mat_por_punto=entrada.df_materiales_por_punto,
                df_costos_por_punto=df_costos_por_punto,
                df_costos_estructura=df_costos_estructuras,
                df_precios_estructura=df_precios_estructura,  # 🔥 AQUÍ
                datos_proyecto=datos_proyecto,
            )),
        ]

        # =====================================================
        # EJECUCIÓN
        # =====================================================
        for nombre_archivo, fn in tasks:

            contenido, err = _safe_exec(nombre_archivo, fn)

            if err:
                errores.append(err)
                continue

            if contenido:
                _add_file(archivos, errores, nombre_archivo, contenido)

        return {
            "archivos": archivos,
            "errores": errores,
            "debug": debug,
        }

    except Exception as e:
        return _fail(str(e), {"traceback": traceback.format_exc()})
