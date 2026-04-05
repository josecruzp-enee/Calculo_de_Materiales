# -*- coding: utf-8 -*-

import pandas as pd

from materiales.auxiliares.materiales_aux import limpiar_codigo, expandir_lista_codigos
from materiales.auxiliares.lector_materiales import leer_hoja_materiales


def calcular_materiales_por_punto(archivo_materiales, estructuras_por_punto, tension):
    """
    Calcula materiales por punto agrupados.
    """

    resumen_punto = []
    cache = {}

    for punto, estructuras in estructuras_por_punto.items():

        for est in estructuras:

            for parte in expandir_lista_codigos(est):

                codigo, _ = limpiar_codigo(parte)

                if not codigo:
                    continue

                try:
                    # =========================
                    # CACHE (evita leer Excel varias veces)
                    # =========================
                    if codigo not in cache:
                        df = leer_hoja_materiales(archivo_materiales, codigo, tension)
                        cache[codigo] = df
                    else:
                        df = cache[codigo]

                    if df is None or df.empty:
                        continue

                    dfp = df.copy()
                    dfp["Punto"] = punto

                    resumen_punto.append(
                        dfp[["Punto", "Materiales", "Unidad", "Cantidad"]]
                    )

                except Exception:
                    continue

    if not resumen_punto:
        return pd.DataFrame(columns=["Punto", "Materiales", "Unidad", "Cantidad"])

    df_final = pd.concat(resumen_punto, ignore_index=True)

    return (
        df_final
        .groupby(["Punto", "Materiales", "Unidad"], as_index=False)["Cantidad"]
        .sum()
    )
