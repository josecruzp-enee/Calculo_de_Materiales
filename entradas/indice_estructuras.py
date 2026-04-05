# -*- coding: utf-8 -*-

import pandas as pd

from entradas.leer_excel import leer_indice_materiales

# 🔧 FIX LOCAL (evita dependencia rota)
def _normalizar_codigo(x):
    if x is None:
        return ""
    return str(x).strip().upper()


def cargar_indice_normalizado(archivo_materiales, log) -> pd.DataFrame:

    if not callable(log):
        log = lambda *args, **kwargs: None

    # 🔥 FIX
    df_indice = leer_indice_materiales(archivo_materiales)

    log("Columnas originales índice: " + str(df_indice.columns.tolist()))

    df_indice = df_indice.copy()
    df_indice.columns = df_indice.columns.str.strip().str.lower()

    if "código de estructura" in df_indice.columns:
        df_indice.rename(columns={"código de estructura": "codigodeestructura"}, inplace=True)

    if "codigo de estructura" in df_indice.columns:
        df_indice.rename(columns={"codigo de estructura": "codigodeestructura"}, inplace=True)

    if "descripcion" in df_indice.columns:
        df_indice.rename(columns={"descripcion": "Descripcion"}, inplace=True)

    if "codigodeestructura" not in df_indice.columns:
        raise ValueError("El índice no contiene columna 'codigodeestructura'")

    df_indice["codigodeestructura"] = (
        df_indice["codigodeestructura"]
        .astype(str)
        .map(_normalizar_codigo)
    )

    df_indice = df_indice[df_indice["codigodeestructura"] != ""]

    if "Descripcion" not in df_indice.columns:
        df_indice["Descripcion"] = ""
    else:
        df_indice["Descripcion"] = (
            df_indice["Descripcion"]
            .fillna("")
            .astype(str)
        )

    log("Columnas normalizadas índice: " + str(df_indice.columns.tolist()))
    log("Primeras filas índice:\n" + str(df_indice.head(10)))

    return df_indice
