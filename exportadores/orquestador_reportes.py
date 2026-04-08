# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Any
import traceback


# =========================================================
# 📄 PDFs
# =========================================================
from exportadores.pdf_reportes_simples import (
    generar_pdf_estructuras_global,
    generar_pdf_estructuras_por_punto,
    generar_pdf_materiales,
    generar_pdf_materiales_por_punto,
)

from exportadores.pdf_completo import generar_pdf_completo

# 🔥 NUEVOS ANEXOS
from exportadores.pdf_anexos_costos import (
    tabla_costos_materiales_pdf,
    tabla_costos_estructuras_pdf,
    tabla_costos_por_punto_pdf,
)

# =========================================================
# 📊 EXCEL
# =========================================================
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
# 📄 GENERADORES BASE
# =========================================================
def _gen_estructuras_global(df, nombre):
    _validar_df(df, "df_estructuras", ["Punto"])
    return generar_pdf_estructuras_global(df, nombre)


def _gen_estructuras_por_punto(df, nombre):
    _validar_df(df, "df_estructuras", ["Punto"])
    return generar_pdf_estructuras_por_punto(df, nombre)


def _gen_materiales(df, nombre):
    _validar_df(df, "df_materiales", ["Materiales"])
    return generar_pdf_materiales(df, nombre)


def _gen_materiales_por_punto(df, nombre):
    _validar_df(df, "df_por_punto", ["Punto"])
    return generar_pdf_materiales_por_punto(df, nombre)


def _gen_pdf_completo(df_e, df_m, df_p, nombre):
    return generar_pdf_completo(
        df_mat=df_m,
        df_estructuras=df_e,
        df_estructuras_por_punto=df_e,
        df_mat_por_punto=df_p,
        datos_proyecto={"nombre": nombre},
    )


def _gen_excel(df_r, df_e, df_p, nombre):
    ruta = f"{nombre}_reporte.xlsx"

    return exportar_excel(
        df_resumen=df_r,
        df_estructuras_resumen=df_e,
        df_resumen_por_punto=df_p,
        df_adicionales=None,
        ruta_excel=ruta,
    )


# =========================================================
# 🔥 NUEVOS GENERADORES COSTOS
# =========================================================
def _gen_anexo_costos_materiales(df_costos):
    return tabla_costos_materiales_pdf(df_costos)


def _gen_anexo_costos_estructuras(df_costos_estructuras):
    return tabla_costos_estructuras_pdf(df_costos_estructuras)


def _gen_anexo_costos_por_punto(df_costos_por_punto):
    return tabla_costos_por_punto_pdf(df_costos_por_punto)


# =========================================================
# 🚀 ORQUESTADOR PRINCIPAL
# =========================================================
def generar_reportes(data: Dict[str, Any]) -> Dict[str, Any]:

    archivos: Dict[str, bytes] = {}
    errores: list[str] = []
    debug: dict = {}

    # -----------------------------------------------------
    # INPUT BASE
    # -----------------------------------------------------
    df_e = data.get("df_estructuras")
    df_m = data.get("df_materiales")
    df_r = data.get("df_resumen")
    df_p = data.get("df_por_punto")

    nombre = data.get("nombre_proyecto", "Proyecto")

    # 🔥 NUEVO BLOQUE COSTOS
    costos = data.get("costos", {})

    df_costos_materiales = costos.get("df_costos_materiales")
    df_costos_estructuras = costos.get("df_costos_estructuras")
    df_costos_por_punto = costos.get("df_costos_por_punto")

    debug["input"] = {
        "df_estructuras": type(df_e).__name__,
        "df_materiales": type(df_m).__name__,
        "df_costos": list(costos.keys()) if costos else None,
    }

    # =====================================================
    # 📄 TAREAS
    # =====================================================
    tasks = [
        # 🔹 BASE
        ("estructuras_global.pdf", lambda: _gen_estructuras_global(df_e, nombre)),
        ("estructuras_por_punto.pdf", lambda: _gen_estructuras_por_punto(df_e, nombre)),
        ("materiales.pdf", lambda: _gen_materiales(df_m, nombre)),
        ("materiales_por_punto.pdf", lambda: _gen_materiales_por_punto(df_p, nombre)),

        # 🔹 COMPLETO
        ("reporte_completo.pdf", lambda: _gen_pdf_completo(df_e, df_m, df_p, nombre)),

        # 🔹 COSTOS (🔥 NUEVO)
        ("anexo_costos_materiales.pdf", lambda: _gen_anexo_costos_materiales(df_costos_materiales)),
        ("anexo_costos_estructuras.pdf", lambda: _gen_anexo_costos_estructuras(df_costos_estructuras)),
        ("anexo_costos_por_punto.pdf", lambda: _gen_anexo_costos_por_punto(df_costos_por_punto)),

        # 🔹 EXCEL
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
