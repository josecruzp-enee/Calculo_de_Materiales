# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Any
import traceback
import streamlit as st

# PDFs
from exportadores.pdf_reportes_simples import (
    generar_pdf_estructuras_global,
    generar_pdf_estructuras_por_punto,
    generar_pdf_materiales,
    generar_pdf_materiales_por_punto,
)

# Excel
from exportadores.excel_utils import exportar_excel


# =========================================================
# ORQUESTADOR PRINCIPAL
# =========================================================

def generar_reportes(data: Dict[str, Any]) -> Dict[str, Any]:

    archivos: Dict[str, bytes] = {}
    errores: list[str] = []

    debug_exportadores = {}

    # -----------------------------------------------------
    # EXTRAER DATA
    # -----------------------------------------------------
    df_estructuras = data.get("df_estructuras")
    df_materiales = data.get("df_materiales")
    df_resumen = data.get("df_resumen")
    df_por_punto = data.get("df_por_punto")

    debug_exportadores["INPUT"] = {
        "df_estructuras": type(df_estructuras).__name__,
        "df_materiales": type(df_materiales).__name__,
        "df_resumen": type(df_resumen).__name__,
        "df_por_punto": type(df_por_punto).__name__,
    }

    # =====================================================
    # PDF: ESTRUCTURAS GLOBAL
    # =====================================================
    try:
        if df_estructuras is not None:
            pdf = generar_pdf_estructuras_global(df_estructuras)

            debug_exportadores["estructuras_global"] = {
                "tipo": str(type(pdf)),
                "ok": isinstance(pdf, (bytes, bytearray)),
            }

            if isinstance(pdf, (bytes, bytearray)):
                archivos["estructuras_global.pdf"] = pdf
            else:
                errores.append("estructuras_global devolvió tipo inválido")

    except Exception:
        errores.append("Error en estructuras_global")
        debug_exportadores["estructuras_global"] = {
            "error": traceback.format_exc()
        }

    # =====================================================
    # PDF: ESTRUCTURAS POR PUNTO
    # =====================================================
    try:
        if df_estructuras is not None:
            pdf = generar_pdf_estructuras_por_punto(df_estructuras)

            debug_exportadores["estructuras_por_punto"] = {
                "tipo": str(type(pdf)),
                "ok": isinstance(pdf, (bytes, bytearray)),
            }

            if isinstance(pdf, (bytes, bytearray)):
                archivos["estructuras_por_punto.pdf"] = pdf
            else:
                errores.append("estructuras_por_punto devolvió tipo inválido")

    except Exception:
        errores.append("Error en estructuras_por_punto")
        debug_exportadores["estructuras_por_punto"] = {
            "error": traceback.format_exc()
        }

    # =====================================================
    # PDF: MATERIALES
    # =====================================================
    try:
        if df_materiales is not None:
            pdf = generar_pdf_materiales(df_materiales)

            debug_exportadores["materiales"] = {
                "tipo": str(type(pdf)),
                "ok": isinstance(pdf, (bytes, bytearray)),
            }

            if isinstance(pdf, (bytes, bytearray)):
                archivos["materiales.pdf"] = pdf
            else:
                errores.append("materiales devolvió tipo inválido")

    except Exception:
        errores.append("Error en materiales")
        debug_exportadores["materiales"] = {
            "error": traceback.format_exc()
        }

    # =====================================================
    # PDF: MATERIALES POR PUNTO
    # =====================================================
    try:
        if df_por_punto is not None:
            pdf = generar_pdf_materiales_por_punto(df_por_punto)

            debug_exportadores["materiales_por_punto"] = {
                "tipo": str(type(pdf)),
                "ok": isinstance(pdf, (bytes, bytearray)),
            }

            if isinstance(pdf, (bytes, bytearray)):
                archivos["materiales_por_punto.pdf"] = pdf
            else:
                errores.append("materiales_por_punto devolvió tipo inválido")

    except Exception:
        errores.append("Error en materiales_por_punto")
        debug_exportadores["materiales_por_punto"] = {
            "error": traceback.format_exc()
        }

    # =====================================================
    # EXCEL
    # =====================================================
    try:
        if df_resumen is not None:
            excel_bytes = exportar_excel(
                df_resumen=df_resumen,
                df_estructuras_resumen=df_estructuras,
                df_resumen_por_punto=df_por_punto,
                df_adicionales=None,
            )

            debug_exportadores["excel"] = {
                "tipo": str(type(excel_bytes)),
                "ok": isinstance(excel_bytes, (bytes, bytearray)),
            }

            if isinstance(excel_bytes, (bytes, bytearray)):
                archivos["reporte.xlsx"] = excel_bytes
            else:
                errores.append("excel devolvió tipo inválido")

    except Exception:
        errores.append("Error en excel")
        debug_exportadores["excel"] = {
            "error": traceback.format_exc()
        }

    # =====================================================
    # GUARDAR DEBUG GLOBAL 🔥
    # =====================================================
    debug_pipeline = st.session_state.get("debug_pipeline", {})
    debug_pipeline["EXPORTADORES"] = {
        "archivos_generados": list(archivos.keys()),
        "errores": errores,
        "detalle": debug_exportadores,
    }
    st.session_state["debug_pipeline"] = debug_pipeline

    # =====================================================
    # RESULTADO FINAL
    # =====================================================
    return {
        "archivos": archivos,
        "errores": errores,
    }
