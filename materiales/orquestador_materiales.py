# -*- coding: utf-8 -*-

from __future__ import annotations
import pandas as pd

# =========================
# MODELOS
# =========================
from materiales.modelos.entrada import EntradaMateriales
from materiales.modelos.salida import ResultadoMateriales

# =========================
# MOTOR (🔥 ESTE ES EL CAMBIO CLAVE)
# =========================
from materiales.calculos.calculo_materiales import calcular_materiales_proyecto

# ⚠️ TEMPORAL
from core.cables_materiales import materiales_desde_cables


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


# =========================================================
# ORQUESTADOR
# =========================================================
def ejecutar_materiales(entrada: EntradaMateriales) -> ResultadoMateriales:

    warnings = []

    estructuras_df = entrada.estructuras_df
    tension = entrada.tension
    df_cables = entrada.df_cables

    # =====================================================
    # VALIDACIÓN BÁSICA
    # =====================================================
    if estructuras_df is None or estructuras_df.empty:
        return ResultadoMateriales(
            ok=False,
            df_materiales=pd.DataFrame(),
            errores=["No hay estructuras"],
            warnings=[]
        )

    # =====================================================
    # CÁLCULO (🔥 MOTOR)
    # =====================================================
    try:
        resultados = calcular_materiales_proyecto(
            hojas_base=None,  # aquí luego conectas base real
            df_estructuras=estructuras_df,
            tension=tension
        )

        df_materiales = resultados.get("df_materiales_detalle")

    except Exception as e:
        return ResultadoMateriales(
            ok=False,
            df_materiales=pd.DataFrame(),
            errores=[f"Error en cálculo: {e}"],
            warnings=warnings
        )

    # =====================================================
    # CABLES
    # =====================================================
    df_cables_mat = materiales_desde_cables(df_cables)

    # =====================================================
    # NORMALIZACIÓN
    # =====================================================
    df_materiales = _normalizar_df(df_materiales)
    df_cables_mat = _normalizar_df(df_cables_mat)

    # =====================================================
    # CONSOLIDACIÓN FINAL
    # =====================================================
    df_total = pd.concat([df_materiales, df_cables_mat], ignore_index=True)

    if not df_total.empty:
        df_total = (
            df_total
            .groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"]
            .sum()
            .sort_values("Materiales")
        )

    # =====================================================
    # RESULTADO
    # =====================================================
    return ResultadoMateriales(
        ok=True,
        df_materiales=df_total,
        errores=[],
        warnings=warnings
    )
