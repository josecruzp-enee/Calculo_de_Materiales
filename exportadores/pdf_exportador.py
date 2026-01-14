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


def generar_pdfs(resultados: dict) -> dict:
    """
    Recibe:
      resultados = {
        "datos_proyecto": dict,
        "df_resumen": DataFrame,
        "df_estructuras_resumen": DataFrame,
        "df_estructuras_por_punto": DataFrame,
        "df_resumen_por_punto": DataFrame,
        ...
      }

    Devuelve:
      {"materiales": bytes, "estructuras_global": bytes, ...}
    """
    dp = resultados["datos_proyecto"]
    nombre = dp.get("nombre_proyecto", "Proyecto")

    df_resumen = resultados["df_resumen"]
    df_eg = resultados["df_estructuras_resumen"]
    df_ep = resultados["df_estructuras_por_punto"]
    df_mpp = resultados["df_resumen_por_punto"]

    return {
        "materiales": generar_pdf_materiales(df_resumen, nombre, dp),
        "estructuras_global": generar_pdf_estructuras_global(df_eg, nombre),
        "estructuras_por_punto": generar_pdf_estructuras_por_punto(df_ep, nombre),
        "materiales_por_punto": generar_pdf_materiales_por_punto(df_mpp, nombre),
        "completo": generar_pdf_completo(df_resumen, df_eg, df_ep, df_mpp, dp),
    }

