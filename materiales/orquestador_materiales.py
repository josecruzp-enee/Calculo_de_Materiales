# -*- coding: utf-8 -*-

from __future__ import annotations
import pandas as pd

from materiales.modelos.entrada import EntradaMateriales
from materiales.modelos.salida import ResultadoMateriales

from materiales.calculos.calculo_materiales import calcular_materiales_proyecto
from materiales.validaciones.materiales_validacion import validar_datos_proyecto

from materiales.cables.cables_materiales import materiales_desde_cables


COLUMNAS_STD = ["Materiales", "Unidad", "Cantidad"]


# =========================================================
# HELPERS
# =========================================================
def _normalizar_df(df: pd.DataFrame | None) -> pd.DataFrame:

    if df is None or df.empty:
        return pd.DataFrame(columns=COLUMNAS_STD)

    df = df.copy()

    for col in COLUMNAS_STD:
        if col not in df.columns:
            df[col] = 0.0 if col == "Cantidad" else ""

    df["Materiales"] = df["Materiales"].astype(str).str.strip()
    df["Unidad"] = df["Unidad"].astype(str).str.strip()
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)

    return df[COLUMNAS_STD]


def _consolidar(df: pd.DataFrame) -> pd.DataFrame:

    if df.empty:
        return df

    return (
        df
        .groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"]
        .sum()
    )


# =========================================================
# ORQUESTADOR
# =========================================================
def ejecutar_materiales(
    entrada: EntradaMateriales,
    catalogo: pd.DataFrame | None = None
) -> ResultadoMateriales:

    # =========================
    # 1. VALIDACIÓN BASE
    # =========================
    if entrada.estructuras_df is None or entrada.estructuras_df.empty:
        return ResultadoMateriales(False, pd.DataFrame(), ["Sin estructuras"], [])

    if entrada.hojas_base is None:
        return ResultadoMateriales(False, pd.DataFrame(), ["Base de datos no cargada"], [])

    datos = entrada.datos_proyecto or {}

    # =========================
    # 2. TENSIÓN (FUENTE ÚNICA)
    # =========================
    if entrada.tension is None or entrada.tension == 0:
        return ResultadoMateriales(False, pd.DataFrame(), ["Tensión inválida"], [])

    tension = float(entrada.tension)

    # solo extraer calibre
    try:
        _, calibre_mt = validar_datos_proyecto(datos)
    except Exception as e:
        return ResultadoMateriales(False, pd.DataFrame(), [f"Error validando datos: {e}"], [])

    # =========================
    # 3. CÁLCULO BASE
    # =========================
    try:
        resultados = calcular_materiales_proyecto(
            hojas_base=entrada.hojas_base,
            df_estructuras=entrada.estructuras_df,
            tension=tension
        )

        if not isinstance(resultados, dict):
            raise ValueError("Salida inválida del motor")

        df_materiales = resultados.get("df_materiales_detalle")

        if not isinstance(df_materiales, pd.DataFrame):
            raise ValueError("df_materiales inválido")

        for col in COLUMNAS_STD:
            if col not in df_materiales.columns:
                raise ValueError(f"Falta columna {col}")

    except Exception as e:
        return ResultadoMateriales(False, pd.DataFrame(), [f"Error en cálculo: {e}"], [])

    # =========================
    # 4. CABLES → MATERIALES
    # =========================
    try:
        df_cables_mat = materiales_desde_cables(entrada.df_cables)
    except Exception as e:
        print(f"[WARN] Error en cables: {e}")
        df_cables_mat = pd.DataFrame(columns=COLUMNAS_STD)

    # =========================
    # 5. NORMALIZACIÓN
    # =========================
    df_materiales = _normalizar_df(df_materiales)
    df_cables_mat = _normalizar_df(df_cables_mat)

    # =========================
    # 6. UNIÓN
    # =========================
    df_total = pd.concat([df_materiales, df_cables_mat], ignore_index=True)

    # =========================
    # 6.1 MATERIALES EXTRA
    # =========================
    df_extra = datos.get("materiales_extra")

    if isinstance(df_extra, pd.DataFrame) and not df_extra.empty:
        df_extra = _normalizar_df(df_extra)
        df_total = pd.concat([df_total, df_extra], ignore_index=True)

    # =========================
    # 7. CONSOLIDACIÓN
    # =========================
    df_total = _consolidar(df_total)

    # =========================
    # 7.1 VALIDACIÓN CONTRA CATÁLOGO
    # =========================
    if catalogo is not None and not catalogo.empty:

        catalogo_base = catalogo.copy()

        catalogo_base["Materiales"] = (
            catalogo_base["Materiales"]
            .astype(str)
            .str.upper()
            .str.strip()
        )

        df_total["Materiales"] = (
            df_total["Materiales"]
            .astype(str)
            .str.upper()
            .str.strip()
        )

        catalogo_set = set(catalogo_base["Materiales"])

        no_validos = df_total.loc[~df_total["Materiales"].isin(catalogo_set)]

        if not no_validos.empty:
            errores = [
                f"Material no válido: {m}"
                for m in no_validos["Materiales"].unique()
            ]

            return ResultadoMateriales(False, pd.DataFrame(), errores, [])

    # =========================
    # 8. COSTOS (OPCIONAL)
    # =========================
    if catalogo is not None and not catalogo.empty and "Costo" in catalogo.columns:

        catalogo_tmp = catalogo.copy()

        catalogo_tmp["Materiales"] = (
            catalogo_tmp["Materiales"]
            .astype(str)
            .str.upper()
            .str.strip()
        )

        df_total = df_total.merge(
            catalogo_tmp[["Materiales", "Costo"]],
            on="Materiales",
            how="left"
        )

        df_total["Costo"] = pd.to_numeric(df_total["Costo"], errors="coerce").fillna(0)
        df_total["Costo_Total"] = df_total["Cantidad"] * df_total["Costo"]

    # =========================
    # 9. SALIDA
    # =========================
    return ResultadoMateriales(True, df_total, [], [])
