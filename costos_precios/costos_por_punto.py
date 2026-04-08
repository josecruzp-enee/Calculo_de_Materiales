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

    # -----------------------------
    # VALIDACIÓN
    # -----------------------------
    if df_estructuras_por_punto is None or df_estructuras_por_punto.empty:
        raise ValueError("df_estructuras_por_punto vacío")

    if df_costos_estructuras is None or df_costos_estructuras.empty:
        raise ValueError("df_costos_estructuras vacío")

    required_cols = {"codigodeestructura", "Costo Unitario", "Precio Unitario"}
    if not required_cols.issubset(df_costos_estructuras.columns):
        raise ValueError(f"df_costos_estructuras debe tener {required_cols}")

    # -----------------------------
    # MAPAS
    # -----------------------------
    df_costos_estructuras["codigodeestructura"] = (
        df_costos_estructuras["codigodeestructura"].astype(str).str.strip()
    )

    dict_costo = dict(
        zip(
            df_costos_estructuras["codigodeestructura"],
            df_costos_estructuras["Costo Unitario"]
        )
    )

    dict_precio = dict(
        zip(
            df_costos_estructuras["codigodeestructura"],
            df_costos_estructuras["Precio Unitario"]
        )
    )

    # -----------------------------
    # DETALLE
    # -----------------------------
    resultados = []

    for _, row in df_estructuras_por_punto.iterrows():

        punto = row.get("Punto")
        estructura = str(row.get("codigodeestructura", "")).strip()
        cantidad = float(row.get("Cantidad", 0) or 0)

        costo_unit = float(dict_costo.get(estructura, 0))
        precio_unit = float(dict_precio.get(estructura, 0))

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

    # -----------------------------
    # RESUMEN COSTOS
    # -----------------------------
    df_resumen_costos = (
        df_detalle.groupby("Punto")["Subtotal Costo"]
        .sum()
        .reset_index()
        .rename(columns={"Subtotal Costo": "TOTAL_COSTO_PUNTO"})
    )

    # -----------------------------
    # RESUMEN PRECIOS
    # -----------------------------
    df_resumen_precios = (
        df_detalle.groupby("Punto")["Subtotal Precio"]
        .sum()
        .reset_index()
        .rename(columns={"Subtotal Precio": "TOTAL_PRECIO_PUNTO"})
    )

    return df_detalle, df_resumen_costos, df_resumen_precios
