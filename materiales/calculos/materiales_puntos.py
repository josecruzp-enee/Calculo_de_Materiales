def calcular_materiales_estructura(
    hojas_base,
    estructura,
    cantidad,
    tension,
    calibre_mt=None,
    tabla_conectores_mt=None,
):

    estructura = _normalizar_codigo(estructura)

    if not estructura:
        raise ValueError("Estructura vacía")

    try:
        cantidad = float(cantidad)
    except Exception:
        raise ValueError(f"Cantidad inválida para {estructura}: {cantidad}")

    if cantidad <= 0:
        raise ValueError(f"Cantidad inválida para {estructura}: {cantidad}")

    # 🔥 VALIDAR HOJA
    df_hoja = hojas_base.get(estructura)

    if df_hoja is None or not isinstance(df_hoja, pd.DataFrame):
        raise ValueError(f"Estructura no encontrada o inválida: {estructura}")

    # 🔥 LEER HOJA CON PROTECCIÓN
    try:
        df_filtrado = leer_hoja_materiales(df_hoja, tension)
    except Exception as e:
        raise RuntimeError(f"Error leyendo hoja {estructura}: {e}")

    if df_filtrado is None or df_filtrado.empty:
        raise ValueError(f"Sin materiales para {estructura} @ {tension}")

    df_filtrado = df_filtrado.copy()

    # 🔥 NORMALIZAR COLUMNAS
    df_filtrado.columns = [str(c).strip() for c in df_filtrado.columns]

    # 🔥 VALIDAR COLUMNAS
    if not set(COLUMNAS_STD).issubset(df_filtrado.columns):
        raise ValueError(
            f"Formato inválido en hoja {estructura}: {list(df_filtrado.columns)}"
        )

    # 🔥 NORMALIZAR CANTIDAD
    df_filtrado["Cantidad"] = pd.to_numeric(
        df_filtrado["Cantidad"], errors="coerce"
    ).fillna(0.0)

    df_filtrado["Cantidad"] *= cantidad

    return df_filtrado[COLUMNAS_STD]
