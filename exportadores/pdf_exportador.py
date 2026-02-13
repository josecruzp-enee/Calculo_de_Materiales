# -*- coding: utf-8 -*-
"""
exportadores/pdf_exportador.py
Genera PDFs a partir de resultados ya calculados (DFs + datos_proyecto).
"""

from exportadores.pdf_utils import (
    generar_pdf_materiales,
    generar_pdf_estructuras_global,
    generar_pdf_estructuras_por_punto,
    generar_pdf_materiales_por_punto,
    generar_pdf_completo,
)

from core.costos_mano_obra import calcular_mo_desde_indice

_REQUERIDAS = (
    "datos_proyecto",
    "df_resumen",
    "df_estructuras_resumen",
    "df_estructuras_por_punto",
    "df_resumen_por_punto",
)

def _conteo_desde_df_estructuras(df_eg):
    """
    Construye dict {codigo: cantidad} desde df_estructuras_resumen.
    Espera columnas: 'codigodeestructura' y 'Cantidad' (o tolera variantes comunes).
    """
    dfe = df_eg.copy()
    dfe.columns = [str(c).strip() for c in dfe.columns]

    # alias defensivos
    if "codigodeestructura" not in dfe.columns:
        if "Código de Estructura" in dfe.columns:
            dfe["codigodeestructura"] = dfe["Código de Estructura"]
        elif "Estructura" in dfe.columns:
            dfe["codigodeestructura"] = dfe["Estructura"]
        else:
            dfe["codigodeestructura"] = ""

    if "Cantidad" not in dfe.columns:
        if "cantidad" in dfe.columns:
            dfe["Cantidad"] = dfe["cantidad"]
        else:
            dfe["Cantidad"] = 0

    dfe["codigodeestructura"] = dfe["codigodeestructura"].astype(str).str.strip()
    dfe["Cantidad"] = dfe["Cantidad"].fillna(0)

    conteo = {}
    for _, r in dfe.iterrows():
        cod = str(r.get("codigodeestructura", "")).strip()
        if not cod:
            continue
        try:
            qty = int(float(r.get("Cantidad", 0) or 0))
        except Exception:
            qty = 0
        if qty > 0:
            conteo[cod] = conteo.get(cod, 0) + qty

    return conteo


def generar_pdfs(resultados: dict, membrete_pdf: str = "SMART") -> dict:
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

    if any(x is None for x in (df_resumen, df_eg, df_ep, df_mpp)):
        raise ValueError("Uno o más DataFrames vienen como None en 'resultados'.")

    # ✅ costos materiales (si aplica)
    df_costos = resultados.get("df_costos_materiales", None)

    # ✅ ruta Excel base (Estructura_datos.xlsx)
    ruta_datos_materiales = resultados.get("ruta_datos_materiales")

    # ✅ conteo para MO desde resumen de estructuras
    conteo_estructuras = _conteo_desde_df_estructuras(df_eg)

    # ✅ MO desde indice (Precio)
    df_mo_estructuras = None
    if ruta_datos_materiales:
        df_mo_estructuras = calcular_mo_desde_indice(
            archivo_materiales=ruta_datos_materiales,
            conteo=conteo_estructuras
    )
# si no hay ruta, se omite MO y el PDF igual se genera


    pdf_materiales = generar_pdf_materiales(df_resumen, nombre, dp)
    pdf_estructuras_global = generar_pdf_estructuras_global(df_eg, nombre)
    pdf_estructuras_por_punto = generar_pdf_estructuras_por_punto(df_ep, nombre)
    pdf_materiales_por_punto = generar_pdf_materiales_por_punto(df_mpp, nombre)

    pdf_completo = generar_pdf_completo(
        df_resumen,
        df_eg,
        df_ep,
        df_mpp,
        dp,
        df_costos=df_costos,
        df_mo_estructuras=df_mo_estructuras,  # ✅ ANEXO B (MO)
    )

    return {
        "materiales": pdf_materiales,
        "estructuras_global": pdf_estructuras_global,
        "estructuras_por_punto": pdf_estructuras_por_punto,
        "materiales_por_punto": pdf_materiales_por_punto,
        "completo": pdf_completo,
    }
