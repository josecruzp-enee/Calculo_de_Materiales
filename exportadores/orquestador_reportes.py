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


def _validar_df(df, nombre, columnas):
    if df is None:
        raise ValueError(f"{nombre} es None")

    faltantes = [c for c in columnas if c not in df.columns]
    if faltantes:
        raise ValueError(f"{nombre} no tiene columnas requeridas: {faltantes}")


# =========================================================
# 📄 GENERADORES
# =========================================================

def _gen_estructuras_global(df, nombre):
    _validar_df(df, "df_estructuras", ["Punto"])
    return generar_pdf_estructuras_global(df, nombre)


def _gen_estructuras_por_punto(df, nombre):
    _validar_df(df, "df_estructuras", ["Punto"])
    return generar_pdf_estructuras_por_punto(df, nombre)


def _gen_materiales(df, nombre):
    _validar_df(df, "df_materiales", ["Materiales", "Unidad", "Cantidad"])
    return generar_pdf_materiales(df, nombre)


def _gen_materiales_por_punto(df, nombre):
    _validar_df(df, "df_por_punto", ["Punto", "Materiales", "Unidad", "Cantidad"])
    return generar_pdf_materiales_por_punto(df, nombre)


def _gen_pdf_completo(df_e, df_m, df_p, nombre):
    _validar_df(df_e, "df_estructuras", ["Punto"])
    _validar_df(df_m, "df_materiales", ["Materiales"])
    _validar_df(df_p, "df_por_punto", ["Punto"])

    return generar_pdf_completo(
        df_mat=df_m,
        df_estructuras=df_e,
        df_estructuras_por_punto=df_e,
        df_mat_por_punto=df_p,
        datos_proyecto={"nombre": nombre},
    )


def _gen_excel(df_r, df_e, df_p, nombre):
    if df_r is None:
        raise ValueError("df_resumen es None")

    ruta = f"{nombre}_reporte.xlsx"

    return exportar_excel(
        df_resumen=df_r,
        df_estructuras_resumen=df_e,
        df_resumen_por_punto=df_p,
        df_adicionales=None,
        ruta_excel=ruta,
    )


# =========================================================
# 🚀 ORQUESTADOR PRINCIPAL
# =========================================================

def generar_reportes(data: Dict[str, Any]) -> Dict[str, Any]:

    archivos: Dict[str, bytes] = {}
    errores: list[str] = []
    debug: dict = {}

    # -----------------------------------------------------
    # INPUT
    # -----------------------------------------------------

    df_e = data.get("df_estructuras")
    df_m = data.get("df_materiales")
    df_r = data.get("df_resumen")
    df_p = data.get("df_por_punto")

    nombre = data.get("nombre_proyecto", "Proyecto")

    debug["input"] = {
        "df_estructuras": list(df_e.columns) if df_e is not None else None,
        "df_materiales": list(df_m.columns) if df_m is not None else None,
        "df_resumen": list(df_r.columns) if df_r is not None else None,
        "df_por_punto": list(df_p.columns) if df_p is not None else None,
    }

    # =====================================================
    # 📄 TAREAS
    # =====================================================

    tasks = [
        ("estructuras_global.pdf", lambda: _gen_estructuras_global(df_e, nombre)),
        ("estructuras_por_punto.pdf", lambda: _gen_estructuras_por_punto(df_e, nombre)),
        ("materiales.pdf", lambda: _gen_materiales(df_m, nombre)),
        ("materiales_por_punto.pdf", lambda: _gen_materiales_por_punto(df_p, nombre)),
        ("reporte_completo.pdf", lambda: _gen_pdf_completo(df_e, df_m, df_p, nombre)),
        ("reporte.xlsx", lambda: _gen_excel(df_r, df_e, df_p, nombre)),
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
