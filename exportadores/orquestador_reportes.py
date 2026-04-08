# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Any, Tuple
import traceback
import streamlit as st

# PDFs simples
from exportadores.pdf_reportes_simples import (
    generar_pdf_estructuras_global,
    generar_pdf_estructuras_por_punto,
    generar_pdf_materiales,
    generar_pdf_materiales_por_punto,
)

# PDF completo
from exportadores.pdf_completo import generar_pdf_completo

# Excel
from exportadores.excel_utils import exportar_excel


# =========================================================
# 🧩 HELPERS
# =========================================================

def _safe_punto(df):
    """Asegura que exista columna Punto"""
    if df is not None and "Punto" not in df.columns:
        df["Punto"] = "General"
    return df


def _add_file(archivos, errores, nombre, contenido):
    if isinstance(contenido, (bytes, bytearray)):
        archivos[nombre] = contenido
    else:
        errores.append(f"{nombre} inválido")


def _safe_exec(nombre, fn):
    try:
        return fn(), None
    except Exception as e:
        return None, f"{nombre}: {str(e)}\n{traceback.format_exc()}"


# =========================================================
# 📄 GENERADORES INDIVIDUALES
# =========================================================

def _gen_estructuras_global(df, nombre):
    if df is None:
        return None
    return generar_pdf_estructuras_global(df, nombre)


def _gen_estructuras_por_punto(df, nombre):
    if df is None:
        return None
    return generar_pdf_estructuras_por_punto(df, nombre)


def _gen_materiales(df, nombre):
    if df is None:
        return None
    return generar_pdf_materiales(df, nombre)


def _gen_materiales_por_punto(df, nombre):
    if df is None:
        return None
    return generar_pdf_materiales_por_punto(df, nombre)


def _gen_pdf_completo(df_est, df_mat, df_pp, nombre):
    if df_est is None or df_mat is None:
        return None

    return generar_pdf_completo(
        df_mat=df_mat,
        df_estructuras=df_est,
        df_estructuras_por_punto=df_est,
        df_mat_por_punto=df_pp,
        datos_proyecto={"nombre": nombre},
    )


def _gen_excel(df_resumen, df_est, df_pp):
    if df_resumen is None:
        return None

    return exportar_excel(
        df_resumen=df_resumen,
        df_estructuras_resumen=df_est,
        df_resumen_por_punto=df_pp,
        df_adicionales=None,
        ruta_excel=None,  # 🔥 FIX
    )


# =========================================================
# 🚀 ORQUESTADOR PRINCIPAL
# =========================================================

def generar_reportes(data: Dict[str, Any]) -> Dict[str, Any]:

    archivos: Dict[str, bytes] = {}
    errores: list[str] = []

    # -----------------------------------------------------
    # INPUT
    # -----------------------------------------------------
    df_estructuras = _safe_punto(data.get("df_estructuras"))
    df_materiales = data.get("df_materiales")
    df_resumen = data.get("df_resumen")
    df_por_punto = _safe_punto(data.get("df_por_punto"))

    nombre = data.get("nombre_proyecto", "Proyecto")

    st.write("📊 DEBUG INPUT:", {
        "estructuras": type(df_estructuras).__name__,
        "materiales": type(df_materiales).__name__,
        "resumen": type(df_resumen).__name__,
        "por_punto": type(df_por_punto).__name__,
    })

    # =====================================================
    # 📄 EJECUCIÓN MODULAR
    # =====================================================

    tasks = [
        ("estructuras_global.pdf", lambda: _gen_estructuras_global(df_estructuras, nombre)),
        ("estructuras_por_punto.pdf", lambda: _gen_estructuras_por_punto(df_estructuras, nombre)),
        ("materiales.pdf", lambda: _gen_materiales(df_materiales, nombre)),
        ("materiales_por_punto.pdf", lambda: _gen_materiales_por_punto(df_por_punto, nombre)),
        ("reporte_completo.pdf", lambda: _gen_pdf_completo(df_estructuras, df_materiales, df_por_punto, nombre)),
        ("reporte.xlsx", lambda: _gen_excel(df_resumen, df_estructuras, df_por_punto)),
    ]

    for nombre_archivo, fn in tasks:
        contenido, err = _safe_exec(nombre_archivo, fn)

        if err:
            errores.append(err)
            continue

        if contenido:
            _add_file(archivos, errores, nombre_archivo, contenido)

    # =====================================================
    # DEBUG FINAL
    # =====================================================
    st.session_state["debug_exportadores"] = {
        "archivos": list(archivos.keys()),
        "errores": errores,
    }

    return {
        "archivos": archivos,
        "errores": errores,
    }
