# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional
import pandas as pd
import traceback


# =========================================================
# 📦 CONTRATO
# =========================================================
@dataclass(slots=True)
class EntradaReportes:
    df_estructuras: pd.DataFrame
    df_materiales: pd.DataFrame
    df_materiales_por_punto: pd.DataFrame
    df_estructuras_por_punto: Optional[pd.DataFrame] = None
    base_datos: Optional[Dict[str, Any]] = None

    costos: Optional[Dict[str, Any]] = None
    nombre_proyecto: str = "Proyecto"
    datos_proyecto: Optional[Dict[str, Any]] = None
    df_cables: Optional[pd.DataFrame] = None


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
        errores.append(f"{nombre} inválido (no es bytes)")


def _validar_df(df, nombre):
    if df is None or not isinstance(df, pd.DataFrame):
        raise ValueError(f"{nombre} inválido")

    if df.empty:
        raise ValueError(f"{nombre} vacío")


# =========================================================
# 🚀 ORQUESTADOR
# =========================================================
def generar_reportes(entrada: EntradaReportes) -> Dict[str, Any]:

    debug = {}
    errores_lista = []
    archivos = {}

    try:
        # =====================================================
        # VALIDACIONES
        # =====================================================
        _validar_df(entrada.df_estructuras, "df_estructuras")
        _validar_df(entrada.df_materiales, "df_materiales")
        _validar_df(entrada.df_materiales_por_punto, "df_materiales_por_punto")

        costos = entrada.costos or {}
        resultado_costos_proyecto = costos

        df_costos_estructura = costos.get("df_costos_estructura")
        df_precios_estructura = costos.get("df_precios_estructura")

        nombre = entrada.nombre_proyecto
        datos_proyecto = entrada.datos_proyecto or {}

        # =====================================================
        # 📄 TASKS
        # =====================================================
        tasks = [

            ("estructuras_global.pdf", lambda: generar_pdf_estructuras_global(
                entrada.df_estructuras,
                nombre,
                entrada.base_datos,
                entrada.datos_proyecto
            )),

            ("estructuras_por_punto.pdf", lambda: generar_pdf_estructuras_por_punto(
                entrada.df_estructuras,
                nombre,
                entrada.datos_proyecto
            )),

            ("materiales.pdf", lambda: generar_pdf_materiales(
                entrada.df_materiales,
                nombre,
                entrada.datos_proyecto
            )),

            ("materiales_por_punto.pdf", lambda: generar_pdf_materiales_por_punto(
                entrada.df_materiales_por_punto,
                nombre,
                entrada.datos_proyecto
            )),

            ("reporte_completo.pdf", lambda: generar_pdf_completo(
                df_materiales=entrada.df_materiales,
                df_estructuras=entrada.df_estructuras,
                df_precios_estructura=df_precios_estructura,
                datos_proyecto=datos_proyecto,
                costos=resultado_costos_proyecto,
            )),
        ]

        # =====================================================
        # EJECUCIÓN
        # =====================================================
        for nombre_archivo, fn in tasks:

            contenido, err = _safe_exec(nombre_archivo, fn)

            if err:
                errores_lista.append(err)
                continue

            if contenido:
                _add_file(archivos, errores_lista, nombre_archivo, contenido)
            else:
                errores_lista.append(f"{nombre_archivo}: contenido vacío")

        # =====================================================
        # DEBUG SI TODO FALLA
        # =====================================================
        if not archivos:
            debug["error_general"] = "No se generó ningún archivo"
            debug["cantidad_errores"] = len(errores_lista)

        # =====================================================
        # SALIDA
        # =====================================================
        return {
            "archivos": archivos,
            "errores": errores_lista,
            "debug": debug,
        }

    except Exception as e:
        return _fail(str(e), {
            "traceback": traceback.format_exc()
        })
