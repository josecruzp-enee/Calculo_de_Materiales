# -*- coding: utf-8 -*-
"""
pdf_exportador.py
Genera PDFs a partir de resultados ya calculados (DFs + datos_proyecto).
"""

from modulo.pdf_utils import (
    generar_pdf_materiales,
    generar_pdf_estructuras_global,
    generar_pdf_estructuras_por_punto,
    generar_pdf_materiales_por_punto,
    generar_pdf_completo,
)


_REQUERIDAS = (
    "datos_proyecto",
    "df_resumen",
    "df_estructuras_resumen",
    "df_estructuras_por_punto",
    "df_resumen_por_punto",
)


def generar_pdfs(resultados: dict) -> dict:
    """
    Recibe resultados ya calculados y devuelve bytes de PDFs.
    """
    if not isinstance(resultados, dict):
        raise TypeError("generar_pdfs() esperaba un dict 'resultados'.")

    faltan = [k for k in _REQUERIDAS if k not in resultados]
    if faltan:
        raise KeyError(f"Faltan llaves en resultados: {faltan}")

    dp = resultados.get("datos_proyecto") or {}
    nombre = dp.get("nombre_proyecto", "Proyecto")

    df_resumen = resultados.get("df_resumen")
    df_eg = resultados.get("df_estructuras_resumen")
    df_ep = resultados.get("df_estructuras_por_punto")
    df_mpp = resultados.get("df_resumen_por_punto")

    # Por si algo viene None
    if df_resumen is None or df_eg is None or df_ep is None or df_mpp is None:
        raise ValueError("Uno o más DataFrames vienen como None en 'resultados'.")

    return {
        "materiales": generar_pdf_materiales(df_resumen, nombre, dp),
        "estructuras_global": generar_pdf_estructuras_global(df_eg, nombre),
        "estructuras_por_punto": generar_pdf_estructuras_por_punto(df_ep, nombre),
        "materiales_por_punto": generar_pdf_materiales_por_punto(df_mpp, nombre),
        "completo": generar_pdf_completo(df_resumen, df_eg, df_ep, df_mpp, dp),
    }
