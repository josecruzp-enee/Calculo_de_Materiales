# -*- coding: utf-8 -*-
"""
exportadores/pdf_exportador.py
Genera PDFs a partir de resultados ya calculados (DFs + datos_proyecto).
"""
from core.costos_materiales import construir_costos_desde_resumen

from exportadores.pdf_utils import (
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
    # =========================
    # 1) Validación
    # =========================
    if not isinstance(resultados, dict):
        raise TypeError("generar_pdfs() esperaba un dict 'resultados'.")

    faltan = [k for k in _REQUERIDAS if k not in resultados]
    if faltan:
        raise KeyError(f"Faltan llaves en resultados: {faltan}")

    # =========================
    # 2) Entradas (ya calculadas)
    # =========================
    dp = resultados.get("datos_proyecto") or {}
    nombre = dp.get("nombre_proyecto", "Proyecto")

    df_resumen = resultados.get("df_resumen")
    df_eg = resultados.get("df_estructuras_resumen")
    df_ep = resultados.get("df_estructuras_por_punto")
    df_mpp = resultados.get("df_resumen_por_punto")

    # (Opcional) Si todavía no existe, simplemente quedará None
    df_costos = resultados.get("df_costos_materiales", None)

    # =========================
    # 3) Validación de DataFrames
    # =========================
    if df_resumen is None or df_eg is None or df_ep is None or df_mpp is None:
        raise ValueError("Uno o más DataFrames vienen como None en 'resultados'.")

    # =========================
    # 4) Salidas (PDFs)
    # =========================
    pdf_materiales = generar_pdf_materiales(df_resumen, nombre, dp)
    pdf_estructuras_global = generar_pdf_estructuras_global(df_eg, nombre)
    pdf_estructuras_por_punto = generar_pdf_estructuras_por_punto(df_ep, nombre)
    pdf_materiales_por_punto = generar_pdf_materiales_por_punto(df_mpp, nombre)

    # ✅ Informe completo con anexo de costos (si df_costos existe)
    pdf_completo = generar_pdf_completo(
        df_resumen,
        df_eg,
        df_ep,
        df_mpp,
        dp,
        df_costos=df_costos,  # <-- CLAVE
    )

    return {
        "materiales": pdf_materiales,  # SIN precios (solo lista)
        "estructuras_global": pdf_estructuras_global,
        "estructuras_por_punto": pdf_estructuras_por_punto,
        "materiales_por_punto": pdf_materiales_por_punto,
        "completo": pdf_completo,      # CON anexo de costos si existe df_costos_materiales
    }
