# -*- coding: utf-8 -*-

from __future__ import annotations
import pandas as pd

from materiales.calculos.materiales_puntos import (
    calcular_materiales_por_punto,
    extraer_conteo_estructuras,
)


def calcular_materiales_proyecto(
    hojas_base,
    df_estructuras,
    tension,
    calibre_mt=None,
    tabla_conectores_mt=None,
) -> dict:

    conteo, estructuras_por_punto = extraer_conteo_estructuras(df_estructuras)

    df_materiales = calcular_materiales_por_punto(
        hojas_base=hojas_base,
        df_estructuras=df_estructuras,
        tension=tension,
        calibre_mt=calibre_mt,
        tabla_conectores_mt=tabla_conectores_mt
    )

    if df_materiales is None or df_materiales.empty:
        df_resumen = pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])
    else:
        df_resumen = (
            df_materiales
            .groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"]
            .sum()
        )

    return {
        "df_materiales": df_resumen,
        "df_materiales_detalle": df_materiales,
        "conteo_estructuras": conteo,
        "estructuras_por_punto": estructuras_por_punto,
    }
