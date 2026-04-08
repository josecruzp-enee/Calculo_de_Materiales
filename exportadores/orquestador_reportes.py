# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Any
import traceback

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

def _fix_punto(df):
    """Normaliza columna Punto"""
    if df is None:
        return df

    if "punto" in df.columns and "Punto" not in df.columns:
        df = df.rename(columns={"punto": "Punto"})

    if "Punto" not in df.columns:
        df = df.copy()
        df["Punto"] = "General"

    return df


def _safe_exec(nombre, fn):
    """Ejecuta sin romper flujo"""
    try:
        return fn(), None
    except Exception as e:
        return None, f"{nombre}: {str(e)}\n{traceback.format_exc()}"


def _add_file(archivos, errores, nombre, contenido):
    """Agrega archivo si es válido"""
    if isinstance(contenido, (bytes, bytearray)):
        archivos[nombre] = contenido
    else:
        errores.append(f"{nombre} inválido")


# =========================================================
# 📄 GENERADORES
# =========================================================




def _gen_estructuras_global(df, nombre):
    return generar_pdf_estructuras_global(df, nombre) if df is not None else None


def _gen_estructuras_por_punto(df, nombre):
    return generar_pdf_estructuras_por_punto(df, nombre) if df is not None else None


def _gen_materiales(df, nombre):
    return generar_pdf_materiales(df, nombre) if df is not None else None


def _gen_materiales_por_punto(df, nombre):
    return generar_pdf_materiales_por_punto(df, nombre) if df is not None else None


def _gen_pdf_completo(df_e, df_m, df_p, nombre):
    if df_e is None or df_m is None:
        return None

    return generar_pdf_completo(
        df_mat=df_m,
        df_estructuras=df_e,
        df_estructuras_por_punto=df_e,
        df_mat_por_punto=df_p,
        datos_proyecto={"nombre": nombre},
    )


def _gen_excel(df_r, df_e, df_p):
    if df_r is None:
        return None

    return exportar_excel(
        df_resumen=df_r,
        df_estructuras_resumen=df_e,
        df_resumen_por_punto=df_p,
        df_adicionales=None,
        ruta_excel=None  # 🔥 FIX
    )


# =========================================================
# 🚀 ORQUESTADOR PRINCIPAL
# =========================================================

def generar_reportes(data: Dict[str, Any]) -> Dict[str, Any]:

    archivos: Dict[str, bytes] = {}
    errores: list[str] = []
    debug: dict = {}
    
    # -----------------------------------------------------
    # INPUT NORMALIZADO
    # -----------------------------------------------------
    
    df_e = _fix_punto(data.get("df_estructuras"))
    if df_e is not None:
        df_e.columns = df_e.columns.str.strip().str.lower()
    df_m = data.get("df_materiales")
    df_r = data.get("df_resumen")
    df_p = _fix_punto(data.get("df_por_punto"))
    
    nombre = data.get("nombre_proyecto", "Proyecto")

    debug["input"] = {
        "df_estructuras": type(df_e).__name__,
        "df_materiales": type(df_m).__name__,
        "df_resumen": type(df_r).__name__,
        "df_por_punto": type(df_p).__name__,
    }

    # =====================================================
    # 📄 TAREAS
    # =====================================================
    tasks = [
        ("estructuras_global.pdf", lambda: _gen_estructuras_global(df_e, nombre)),
        ("estructuras_por_punto.pdf", lambda: _gen_estructuras_por_punto(df_e, nombre)),
        ("materiales.pdf", lambda: _gen_materiales(df_m, nombre)),
        ("materiales_por_punto.pdf", lambda: _gen_materiales_por_punto(df_p, nombre)),

        # 🔥 PDF COMPLETO (EL IMPORTANTE)
        ("reporte_completo.pdf", lambda: _gen_pdf_completo(df_e, df_m, df_p, nombre)),

        ("reporte.xlsx", lambda: _gen_excel(df_r, df_e, df_p)),
    ]

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

    # =====================================================
    # OUTPUT
    # =====================================================
    return {
        "archivos": archivos,
        "errores": errores,
        "debug": debug,
    }
