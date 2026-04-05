# -*- coding: utf-8 -*-

from __future__ import annotations
import pandas as pd

from materiales.modelos.entrada import EntradaMateriales
from materiales.modelos.salida import ResultadoMateriales

from materiales.calculos.calculo_materiales import calcular_materiales_proyecto
from materiales.validaciones.materiales_validacion import validar_datos_proyecto

# ✅ YA NO usar core
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
def ejecutar_materiales(entrada: EntradaMateriales) -> ResultadoMateriales:

    # =========================
    # 1. VALIDACIÓN BASE
    # =========================
    if entrada.estructuras_df is None or entrada.estructuras_df.empty:
        return ResultadoMateriales(False, pd.DataFrame(), ["Sin estructuras"], [])

    if entrada.hojas_base is None:
        return ResultadoMateriales(False, pd.DataFrame(), ["Base de datos no cargada"], [])

    datos = entrada.datos_proyecto or {}

    try:
        tension, calibre_mt = validar_datos_proyecto(datos)
    except Exception as e:
        return ResultadoMateriales(False, pd.DataFrame(), [f"Error validando datos: {e}"], [])

    # =========================
    # 2. CÁLCULO BASE
    # =========================
    try:
        resultados = calcular_materiales_proyecto(
            hojas_base=entrada.hojas_base,
            df_estructuras=entrada.estructuras_df,
            tension=tension
        )

        if not isinstance(resultados, dict) or "df_materiales_detalle" not in resultados:
            raise ValueError("Salida inválida de calcular_materiales_proyecto")

        df_materiales = resultados.get("df_materiales_detalle")

    except Exception as e:
        return ResultadoMateriales(False, pd.DataFrame(), [f"Error en cálculo: {e}"], [])

    # =========================
    # 3. CABLES → MATERIALES
    # =========================
    try:
        df_cables_mat = materiales_desde_cables(entrada.df_cables)
    except Exception:
        df_cables_mat = pd.DataFrame(columns=COLUMNAS_STD)

    # =========================
    # 4. NORMALIZACIÓN
    # =========================
    df_materiales = _normalizar_df(df_materiales)
    df_cables_mat = _normalizar_df(df_cables_mat)

    # =========================
    # 5. UNIÓN
    # =========================
    df_total = pd.concat([df_materiales, df_cables_mat], ignore_index=True)

    # =========================
    # 🔥 5.1 MATERIALES EXTRA
    # =========================
    df_extra = datos.get("materiales_extra")

    if isinstance(df_extra, pd.DataFrame) and not df_extra.empty:
        df_extra = _normalizar_df(df_extra)
        df_total = pd.concat([df_total, df_extra], ignore_index=True)

    # =========================
    # 6. CONSOLIDACIÓN
    # =========================
    df_total = _consolidar(df_total)

    # =========================
    # 7. SALIDA
    # =========================
    return ResultadoMateriales(True, df_total, [], [])
