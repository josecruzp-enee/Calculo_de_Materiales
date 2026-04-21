# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from collections import Counter
from entradas.normalizar import limpiar_codigo
from ayuda.debug import debug_guardar


# ==========================================================
# NORMALIZACIÓN
# ==========================================================
def _normalizar_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    SALIDA:
    -------
    DataFrame normalizado:
        - columnas limpias (strip)
    """

    if df is None or df.empty:
        debug_guardar("ESTRUCTURAS", "INPUT", "DF_VACIO", True)
        return pd.DataFrame()

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    debug_guardar("ESTRUCTURAS", "INPUT", "COLUMNAS", list(df.columns))

    return df


def _obtener_columna(df, opciones):
    """
    SALIDA:
    -------
    Nombre real de columna encontrada en el DataFrame
    """

    cols_norm = {
        c.lower().replace(" ", ""): c
        for c in df.columns
    }

    for op in opciones:
        op_norm = op.lower().replace(" ", "")
        if op_norm in cols_norm:
            return cols_norm[op_norm]

    return None


# ==========================================================
# EXTRACCIÓN BASE
# ==========================================================
def _extraer_datos(df_estructuras):
    """
    SALIDA:
    -------
    List[dict] con:
        - Punto
        - Estructura
        - Cantidad
    """

    df = _normalizar_df(df_estructuras)

    if df.empty:
        return []

    col_est = _obtener_columna(df, ["codigo", "estructura"])
    col_punto = _obtener_columna(df, ["punto"])
    col_cant = _obtener_columna(df, ["cantidad", "cant"])

    debug_guardar("ESTRUCTURAS", "COLUMNAS_DETECTADAS", "col_est", col_est)
    debug_guardar("ESTRUCTURAS", "COLUMNAS_DETECTADAS", "col_punto", col_punto)
    debug_guardar("ESTRUCTURAS", "COLUMNAS_DETECTADAS", "col_cant", col_cant)

    if col_est is None:
        raise ValueError(f"No se encontró columna de estructuras: {list(df.columns)}")

    registros = []

    for _, row in df.iterrows():

        estructura = row.get(col_est)
        if not estructura:
            continue

        estructura = limpiar_codigo(estructura)

        punto = row.get(col_punto)
        punto = str(punto).strip() if punto else "General"

        cantidad = row.get(col_cant, 1)
        try:
            cantidad = int(float(cantidad))
        except:
            cantidad = 1

        registros.append({
            "Punto": punto,
            "Estructura": estructura,
            "Cantidad": cantidad
        })

    debug_guardar("ESTRUCTURAS", "PROCESO", "REGISTROS_EXTRAIDOS", len(registros))

    return registros


# ==========================================================
# GLOBAL
# ==========================================================
def calcular_estructuras_global(df_estructuras) -> pd.DataFrame:
    """
    SALIDA:
    -------
    DataFrame:
        - Estructura
        - Cantidad
        - Descripcion
    """

    df = _normalizar_df(df_estructuras)

    if df.empty:
        return pd.DataFrame(columns=["Estructura", "Cantidad", "Descripcion"])

    col_est = _obtener_columna(df, ["codigo", "estructura"])
    col_cant = _obtener_columna(df, ["cantidad", "cant"])
    col_desc = _obtener_columna(df, ["descripcion"])

    debug_guardar("GLOBAL", "COLUMNAS", "col_est", col_est)
    debug_guardar("GLOBAL", "COLUMNAS", "col_cant", col_cant)
    debug_guardar("GLOBAL", "COLUMNAS", "col_desc", col_desc)

    if col_est is None:
        raise ValueError(f"No se encontró columna de estructuras: {list(df.columns)}")

    df_tmp = df.copy()

    df_tmp["Estructura"] = df_tmp[col_est].apply(limpiar_codigo)

    df_tmp["Cantidad"] = pd.to_numeric(
        df_tmp.get(col_cant, 1), errors="coerce"
    ).fillna(1)

    if col_desc:
        df_tmp["Descripcion"] = df_tmp[col_desc].astype(str)
    else:
        df_tmp["Descripcion"] = ""

    df_out = (
        df_tmp
        .groupby("Estructura", as_index=False)
        .agg({
            "Cantidad": "sum",
            "Descripcion": "first"
        })
    )

    debug_guardar("GLOBAL", "RESULTADO", "FILAS", len(df_out))
    debug_guardar("GLOBAL", "RESULTADO", "PREVIEW", df_out.head(10))

    return df_out


# ==========================================================
# POR PUNTO
# ==========================================================
def calcular_estructuras_por_punto(df_estructuras) -> pd.DataFrame:
    """
    SALIDA:
    -------
    DataFrame:
        - Punto
        - Estructura
        - Cantidad
    """

    registros = _extraer_datos(df_estructuras)

    if not registros:
        return pd.DataFrame(columns=["Punto", "Estructura", "Cantidad"])

    df = pd.DataFrame(registros)

    df_out = (
        df
        .groupby(["Punto", "Estructura"], as_index=False)["Cantidad"]
        .sum()
    )

    debug_guardar("POR_PUNTO", "RESULTADO", "FILAS", len(df_out))

    return df_out


# ==========================================================
# DESCRIPCIÓN
# ==========================================================
def generar_descripcion_estructuras(df_estructuras) -> dict:
    """
    SALIDA:
    -------
    dict:
        clave → Punto
        valor → descripción string
    """

    df = calcular_estructuras_por_punto(df_estructuras)

    if df.empty:
        return {}

    resultado = {}

    for punto in sorted(df["Punto"].unique()):

        df_p = df[df["Punto"] == punto]

        partes = [
            f"{row['Estructura']} ({int(row['Cantidad'])})"
            for _, row in df_p.iterrows()
        ]

        resultado[punto] = ", ".join(partes)

    debug_guardar("DESCRIPCION", "RESULTADO", "TOTAL_PUNTOS", len(resultado))

    return resultado


# ==========================================================
# FUNCIÓN PRINCIPAL
# ==========================================================
def calcular_estructuras_proyecto(df_estructuras):
    """
    SALIDA:
    -------
    dict:
        - df_estructuras
        - df_estructuras_por_punto
        - descripcion_estructuras
    """

    resultado = {
        "df_estructuras": calcular_estructuras_global(df_estructuras),
        "df_estructuras_por_punto": calcular_estructuras_por_punto(df_estructuras),
        "descripcion_estructuras": generar_descripcion_estructuras(df_estructuras),
    }

    debug_guardar("PROYECTO", "SALIDA", "CLAVES", list(resultado.keys()))
    debug_guardar("PROYECTO", "SALIDA", "df_estructuras_shape", resultado["df_estructuras"].shape)
    debug_guardar("PROYECTO", "SALIDA", "df_por_punto_shape", resultado["df_estructuras_por_punto"].shape)

    return resultado
