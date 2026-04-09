import pandas as pd


def calcular_costos_por_punto(
    df_estructuras_por_punto: pd.DataFrame,
    df_costos_estructuras: pd.DataFrame,
):
    """
    Retorna:
    - df_detalle
    - df_resumen_costos
    - df_resumen_precios
    """

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    if df_estructuras_por_punto is None or df_estructuras_por_punto.empty:
        raise ValueError("df_estructuras_por_punto vacío")

    if df_costos_estructuras is None or df_costos_estructuras.empty:
        raise ValueError("df_costos_estructuras vacío")

    required_cols = {"codigodeestructura", "Costo Unitario", "Precio Unitario"}
    if not required_cols.issubset(df_costos_estructuras.columns):
        raise ValueError(f"df_costos_estructuras debe tener {required_cols}")

    # =====================================================
    # NORMALIZACIÓN
    # =====================================================
    df_ep = df_estructuras_por_punto.copy()
    df_ce = df_costos_estructuras.copy()

    df_ep["codigodeestructura"] = df_ep["codigodeestructura"].astype(str).str.strip().str.upper()
    df_ce["codigodeestructura"] = df_ce["codigodeestructura"].astype(str).str.strip().str.upper()

    df_ep["Punto"] = df_ep["Punto"].astype(str).str.strip()

    df_ep["Cantidad"] = pd.to_numeric(df_ep["Cantidad"], errors="coerce").fillna(0)

    # =====================================================
    # MAPAS
    # =====================================================
    dict_costo = dict(zip(df_ce["codigodeestructura"], df_ce["Costo Unitario"]))
    dict_precio = dict(zip(df_ce["codigodeestructura"], df_ce["Precio Unitario"]))

    # =====================================================
    # DETALLE
    # =====================================================
    resultados = []

    for _, row in df_ep.iterrows():

        punto = row["Punto"]
        estructura = row["codigodeestructura"]
        cantidad = float(row["Cantidad"])

        # 🔥 VALIDACIÓN CRÍTICA
        if estructura not in dict_costo:
            raise ValueError(f"Estructura sin costo definida: {estructura}")

        costo_unit = float(dict_costo[estructura])
        precio_unit = float(dict_precio[estructura])

        subtotal_costo = cantidad * costo_unit
        subtotal_precio = cantidad * precio_unit

        resultados.append({
            "Punto": punto,
            "codigodeestructura": estructura,
            "Cantidad": cantidad,
            "Costo Unitario": round(costo_unit, 2),
            "Precio Unitario": round(precio_unit, 2),
            "Subtotal Costo": round(subtotal_costo, 2),
            "Subtotal Precio": round(subtotal_precio, 2),
        })

    df_detalle = pd.DataFrame(resultados)

    # =====================================================
    # RESUMEN COSTOS
    # =====================================================
    df_resumen_costos = (
        df_detalle.groupby("Punto")["Subtotal Costo"]
        .sum()
        .reset_index()
        .rename(columns={"Subtotal Costo": "TOTAL_COSTO_PUNTO"})
    )

    # =====================================================
    # RESUMEN PRECIOS
    # =====================================================
    df_resumen_precios = (
        df_detalle.groupby("Punto")["Subtotal Precio"]
        .sum()
        .reset_index()
        .rename(columns={"Subtotal Precio": "TOTAL_PRECIO_PUNTO"})
    )

    return df_detalle, df_resumen_costos, df_resumen_precios
