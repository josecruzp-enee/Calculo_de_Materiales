# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Any
import traceback

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
    """
    Orquesta la generación de todos los reportes exportables.

    Returns:
        {
            "archivos": dict[str, bytes],
            "errores": list[str]
        }
    """

    archivos: Dict[str, bytes] = {}
    errores: list[str] = []

    # -----------------------------------------------------
    # EXTRAER DATA (ajusta según tu estructura real)
    # -----------------------------------------------------
    df_estructuras = data.get("df_estructuras")
    df_materiales = data.get("df_materiales")
    df_resumen = data.get("df_resumen")
    df_por_punto = data.get("df_por_punto")

    # -----------------------------------------------------
    # PDF: ESTRUCTURAS GLOBAL
    # -----------------------------------------------------
    try:
        if df_estructuras is not None:
            pdf = generar_pdf_estructuras_global(df_estructuras)
            if isinstance(pdf, (bytes, bytearray)):
                archivos["estructuras_global.pdf"] = pdf
            else:
                errores.append("estructuras_global devolvió tipo inválido")
    except Exception:
        errores.append("Error en estructuras_global:\n" + traceback.format_exc())

    # -----------------------------------------------------
    # PDF: ESTRUCTURAS POR PUNTO
    # -----------------------------------------------------
    try:
        if df_estructuras is not None:
            pdf = generar_pdf_estructuras_por_punto(df_estructuras)
            if isinstance(pdf, (bytes, bytearray)):
                archivos["estructuras_por_punto.pdf"] = pdf
            else:
                errores.append("estructuras_por_punto devolvió tipo inválido")
    except Exception:
        errores.append("Error en estructuras_por_punto:\n" + traceback.format_exc())

    # -----------------------------------------------------
    # PDF: MATERIALES GLOBAL
    # -----------------------------------------------------
    try:
        if df_materiales is not None:
            pdf = generar_pdf_materiales(df_materiales)
            if isinstance(pdf, (bytes, bytearray)):
                archivos["materiales.pdf"] = pdf
            else:
                errores.append("materiales devolvió tipo inválido")
    except Exception:
        errores.append("Error en materiales:\n" + traceback.format_exc())

    # -----------------------------------------------------
    # PDF: MATERIALES POR PUNTO
    # -----------------------------------------------------
    try:
        if df_por_punto is not None:
            pdf = generar_pdf_materiales_por_punto(df_por_punto)
            if isinstance(pdf, (bytes, bytearray)):
                archivos["materiales_por_punto.pdf"] = pdf
            else:
                errores.append("materiales_por_punto devolvió tipo inválido")
    except Exception:
        errores.append("Error en materiales_por_punto:\n" + traceback.format_exc())

    # -----------------------------------------------------
    # EXCEL
    # -----------------------------------------------------
    try:
        if df_resumen is not None:
            excel_bytes = exportar_excel(
                df_resumen=df_resumen,
                df_estructuras_resumen=df_estructuras,
                df_resumen_por_punto=df_por_punto,
                df_adicionales=None,
            )
            if isinstance(excel_bytes, (bytes, bytearray)):
                archivos["reporte.xlsx"] = excel_bytes
            else:
                errores.append("excel devolvió tipo inválido")
    except Exception:
        errores.append("Error en excel:\n" + traceback.format_exc())

    # -----------------------------------------------------
    # RESULTADO FINAL
    # -----------------------------------------------------
    return {
        "archivos": archivos,
        "errores": errores,
    }
