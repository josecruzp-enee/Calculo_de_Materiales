# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional
import pandas as pd
import traceback


# =========================================================
# 📦 CONTRATO FUERTE
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

    if not isinstance(entrada, EntradaReportes):
        return _fail("entrada debe ser EntradaReportes")

    try:
        # =====================================================
        # VALIDACIÓN BASE
        # =====================================================
        _validar_df(entrada.df_estructuras, "df_estructuras", ["Punto"])
        _validar_df(entrada.df_materiales, "df_materiales", ["Materiales"])
        _validar_df(entrada.df_materiales_por_punto, "df_materiales_por_punto", ["Punto"])

        costos = entrada.costos or {}

        # =====================================================
        # EXTRAER COSTOS (SIN BLOQUEAR)
        # =====================================================
        df_costos_materiales = costos.get("df_materiales_costos")
        df_costos_estructuras = costos.get("df_costos_estructura")
        df_costos_por_punto = costos.get("df_costos_por_punto")

        # limpieza suave
        if isinstance(df_costos_materiales, pd.DataFrame) and df_costos_materiales.empty:
            df_costos_materiales = None

        if isinstance(df_costos_estructuras, pd.DataFrame) and df_costos_estructuras.empty:
            df_costos_estructuras = None

        if isinstance(df_costos_por_punto, pd.DataFrame) and df_costos_por_punto.empty:
            df_costos_por_punto = None

        archivos = {}
        errores = []
        debug = {}

        nombre = entrada.nombre_proyecto

        # =====================================================
        # 📄 BASE
        # =====================================================
        tasks = [
            ("estructuras_global.pdf", lambda: generar_pdf_estructuras_global(entrada.df_estructuras, nombre)),
            ("estructuras_por_punto.pdf", lambda: generar_pdf_estructuras_por_punto(entrada.df_estructuras, nombre)),
            ("materiales.pdf", lambda: generar_pdf_materiales(entrada.df_materiales, nombre)),
            ("materiales_por_punto.pdf", lambda: generar_pdf_materiales_por_punto(entrada.df_materiales_por_punto, nombre)),

            ("reporte_completo.pdf", lambda: generar_pdf_completo(
                df_mat=entrada.df_materiales,
                df_estructuras=entrada.df_estructuras,
                df_estructuras_por_punto=entrada.df_estructuras,
                df_mat_por_punto=entrada.df_materiales_por_punto,
                datos_proyecto={"nombre": nombre},
            )),
        ]

        # =====================================================
        # 💰 COSTOS (OPCIONAL Y ROBUSTO)
        # =====================================================
        if df_costos_materiales is not None:
            tasks.append((
                "anexo_costos_materiales.pdf",
                lambda: tabla_costos_materiales_pdf(df_costos_materiales)
            ))

        if df_costos_estructuras is not None:
            tasks.append((
                "anexo_costos_estructuras.pdf",
                lambda: tabla_costos_estructuras_pdf(df_costos_estructuras)
            ))

        if df_costos_por_punto is not None:
            tasks.append((
                "anexo_costos_por_punto.pdf",
                lambda: tabla_costos_por_punto_pdf(df_costos_por_punto)
            ))

        # =====================================================
        # 📊 EXCEL
        # =====================================================
        tasks.append((
            "reporte.xlsx",
            lambda: exportar_excel(
                df_resumen=entrada.df_materiales,
                df_estructuras_resumen=entrada.df_estructuras,
                df_resumen_por_punto=entrada.df_materiales_por_punto,
                df_adicionales=df_costos_por_punto,
                ruta_excel=f"{nombre}_reporte.xlsx",
            )
        ))

        # =====================================================
        # ⚙️ EJECUCIÓN
        # =====================================================
        for nombre_archivo, fn in tasks:

            contenido, err = _safe_exec(nombre_archivo, fn)

            if err:
                errores.append(err)
                debug[nombre_archivo] = "ERROR"
                continue

            if contenido:
                _add_file(archivos, errores, nombre_archivo, contenido)
                debug[nombre_archivo] = "OK"
            else:
                debug[nombre_archivo] = "EMPTY"

        return {
            "archivos": archivos,
            "errores": errores,
            "debug": debug,
        }

    except Exception as e:
        return _fail(str(e), {"traceback": traceback.format_exc()})
