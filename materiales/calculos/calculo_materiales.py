# -*- coding: utf-8 -*-

from __future__ import annotations
import pandas as pd


from materiales.calculos.materiales_puntos import (
    calcular_materiales_por_punto,
    extraer_conteo_estructuras,
)


# ==========================================================
# MOTOR DE CÁLCULO DE MATERIALES
# ==========================================================
def calcular_materiales_proyecto(
    hojas_base: dict[str, pd.DataFrame],
    df_estructuras: pd.DataFrame,
    tension: float,
    calibre_mt=None,
    tabla_conectores_mt=None,
) -> dict:
    """
    Motor puro de cálculo de materiales.

    NO:
    - lee archivos
    - valida UI
    - calcula costos
    - usa streamlit

    SOLO:
    - calcula materiales
    - calcula estructuras
    """

    # ======================================================
    # 1. Conteo de estructuras
    # ======================================================
    conteo, estructuras_por_punto = extraer_conteo_estructuras(df_estructuras)

    # ======================================================
    # 2. Materiales globales
    # ======================================================
    df_materiales = calcular_materiales_por_punto(
        hojas_base=hojas_base,
        df_estructuras=df_estructuras,
        tension=tension,
        calibre_mt=calibre_mt,
        tabla_conectores_mt=tabla_conectores_mt
    )

    # ======================================================
    # 3. Resumen global
    # ======================================================
    if df_materiales is None or df_materiales.empty:
        df_resumen = pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])
    else:
        df_resumen = (
            df_materiales
            .groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"]
            .sum()
        )

    # ======================================================
    # 4. Resultado
    # ======================================================
    return {
        "df_materiales": df_resumen,
        "conteo_estructuras": conteo,
        "estructuras_por_punto": estructuras_por_punto,
        "df_materiales_detalle": df_materiales,
    }
