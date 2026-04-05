# -*- coding: utf-8 -*-

import pandas as pd

# =========================================================
# MOCK REPORTES (TEMPORAL)
# =========================================================

def generar_reportes(*args, **kwargs):
    """
    Stub temporal para evitar errores de import.
    """
    return {
        "pdf_generado": False,
        "mensaje": "Reportes deshabilitados temporalmente"
    }


def resumen_estructuras(df=None):
    """
    Retorna resumen básico de estructuras.
    """
    if df is None or not hasattr(df, "empty") or df.empty:
        return pd.DataFrame()

    if "Estructura" not in df.columns:
        return pd.DataFrame()

    resumen = (
        df["Estructura"]
        .value_counts()
        .reset_index()
    )

    resumen.columns = ["Estructura", "Cantidad"]

    return resumen
