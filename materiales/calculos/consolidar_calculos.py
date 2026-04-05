# -*- coding: utf-8 -*-

import pandas as pd

from materiales.calculos.materiales_puntos import calcular_materiales_por_punto


COLUMNAS_STD = ["Materiales", "Unidad", "Cantidad"]


def consolidar_calculos_materiales(
    hojas_base,
    df_estructuras,
    tension,
    calibre_mt=None,
    tabla_conectores_mt=None,
) -> pd.DataFrame:
    """
    Consolida los cálculos de materiales del proyecto.

    NO:
    - hace lógica de negocio
    - valida UI
    - calcula estructuras aparte

    SOLO:
    - ejecuta cálculos
    - concatena resultados
    """

    resultados = []

    # =====================================
    # 1. Materiales por proyecto
    # =====================================
    df = calcular_materiales_por_punto(
        hojas_base=hojas_base,
        df_estructuras=df_estructuras,
        tension=tension,
        calibre_mt=calibre_mt,
        tabla_conectores_mt=tabla_conectores_mt,
    )

    if df is not None and not df.empty:
        resultados.append(df)

    # =====================================
    # 2. Consolidación
    # =====================================
    if not resultados:
        return pd.DataFrame(columns=COLUMNAS_STD)

    df_final = pd.concat(resultados, ignore_index=True)

    # =====================================
    # 3. Validación de formato
    # =====================================
    columnas = set(df_final.columns)
    if not set(COLUMNAS_STD).issubset(columnas):
        raise ValueError(f"Formato inválido: {df_final.columns}")

    return df_final[COLUMNAS_STD]
