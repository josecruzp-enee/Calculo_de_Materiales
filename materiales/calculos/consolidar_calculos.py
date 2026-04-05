# -*- coding: utf-8 -*-

import pandas as pd

from materiales.calculos.materiales_puntos import calcular_materiales_por_punto
from materiales.calculos.materiales_estructuras import calcular_materiales_estructuras


def consolidar_calculos_materiales(estructuras_df, tension):

    resultados = []

    # =========================
    # 1. Materiales por punto
    # =========================
    df_puntos = calcular_materiales_por_punto(estructuras_df, tension)
    if df_puntos is not None and not df_puntos.empty:
        resultados.append(df_puntos)

    # =========================
    # 2. Materiales por estructura (si aplica)
    # =========================
    df_est = calcular_materiales_estructuras(estructuras_df, tension)
    if df_est is not None and not df_est.empty:
        resultados.append(df_est)

    # =========================
    # 3. Consolidación interna
    # =========================
    if not resultados:
        return pd.DataFrame()

    return pd.concat(resultados, ignore_index=True)
