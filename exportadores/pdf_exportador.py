# -*- coding: utf-8 -*-
"""
exportadores/pdf_exportador.py
Genera PDFs a partir de resultados ya calculados.
VERSIÓN LIMPIA: usa SOLO PDF correcto (3 secciones)
"""

from exportadores.pdf_utils import (
    generar_pdf_materiales,
    generar_pdf_estructuras_global,
    generar_pdf_estructuras_por_punto,
    generar_pdf_materiales_por_punto,
    generar_pdf_completo,  # ✅ usamos el bueno
)

_REQUERIDAS = (
    "datos_proyecto",
    "df_resumen",
    "df_estructuras_resumen",
    "df_estructuras_por_punto",
    "df_resumen_por_punto",
)


def generar_pdfs(resultados: dict, membrete_pdf: str = "SMART") -> dict:
    """
    Genera PDFs a partir de resultados YA CALCULADOS.
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

    if any(x is None for x in (df_resumen, df_eg, df_ep, df_mpp)):
        raise ValueError("Uno o más DataFrames vienen como None en 'resultados'.")

    # =====================================================
    # 🔥 NUEVO: PRECIOS (OBLIGATORIO PARA PDF LIMPIO)
    # =====================================================
    df_precios_estructura = resultados.get("df_precios_estructura")

    if df_precios_estructura is None:
        raise ValueError(
            "df_precios_estructura no existe. "
            "Debes generarlo antes del PDF."
        )

    # =====================================================
    # GENERACIÓN PDFS (LEGACY SE MANTIENEN)
    # =====================================================
    pdf_materiales = generar_pdf_materiales(df_resumen, nombre, dp)

    pdf_estructuras_global = generar_pdf_estructuras_global(
        df_eg, nombre
    )

    pdf_estructuras_por_punto = generar_pdf_estructuras_por_punto(
        df_ep, nombre
    )

    pdf_materiales_por_punto = generar_pdf_materiales_por_punto(
        df_mpp, nombre
    )

    # =====================================================
    # ✅ PDF COMPLETO LIMPIO
    # =====================================================
    pdf_completo = generar_pdf_completo(
        df_materiales=df_resumen,
        df_estructuras=df_eg,
        df_precios_estructura=df_precios_estructura,
        datos_proyecto=dp,
    )

    return {
        "materiales": pdf_materiales,
        "estructuras_global": pdf_estructuras_global,
        "estructuras_por_punto": pdf_estructuras_por_punto,
        "materiales_por_punto": pdf_materiales_por_punto,
        "completo": pdf_completo,
    }
