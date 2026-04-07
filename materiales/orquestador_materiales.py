# -*- coding: utf-8 -*-
# materiales/orquestador_materiales.py

from __future__ import annotations

from typing import Optional, Dict, Any, List
import pandas as pd

# =========================================================
# IMPORTS DE DOMINIO (PERMITIDOS)
# =========================================================
from materiales.modelos.entrada import EntradaMateriales
from materiales.modelos.salida import ResultadoMateriales

from materiales.calculos.calculo_materiales import (
    calcular_materiales_proyecto,
)

from materiales.validaciones.materiales_validacion import (
    validar_datos_proyecto,
)

# ❌ ELIMINADO:
# from entradas.normalizar import normalizar_estructuras


# =========================================================
# HELPERS
# =========================================================
def _df_vacio() -> pd.DataFrame:
    return pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])


def _merge_materiales(
    df_a: Optional[pd.DataFrame],
    df_b: Optional[pd.DataFrame],
) -> pd.DataFrame:
    """
    Suma dos DataFrames de materiales (Materiales, Unidad, Cantidad).
    """
    if df_a is None or df_a.empty:
        return df_b if isinstance(df_b, pd.DataFrame) else _df_vacio()

    if df_b is None or df_b.empty:
        return df_a

    df = pd.concat([df_a, df_b], ignore_index=True)

    if not set(["Materiales", "Unidad", "Cantidad"]).issubset(df.columns):
        return df

    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0.0)

    df_out = (
        df.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"]
        .sum()
        .sort_values(["Materiales", "Unidad"])
        .reset_index(drop=True)
    )

    return df_out


# =========================================================
# ORQUESTADOR (DOMINIO PURO)
# =========================================================
def ejecutar_materiales(
    *,
    estructuras_df: pd.DataFrame,
    hojas_base: Dict[str, pd.DataFrame],
    datos_proyecto: Optional[Dict[str, Any]] = None,
    df_cables: Optional[pd.DataFrame] = None,
    df_materiales_extra: Optional[pd.DataFrame] = None,
    tension: Optional[float] = None,
) -> ResultadoMateriales:
    """
    Pipeline limpio:

        1) Validación de datos_proyecto
        2) Uso directo de estructuras (YA NORMALIZADAS)
        3) Cálculo de materiales
        4) Integración de cables
        5) Integración de materiales extra
        6) Consolidación final

    🔥 IMPORTANTE:
        Este módulo NO normaliza estructuras
    """

    errores: List[str] = []
    warnings: List[str] = []

    # -----------------------------------------------------
    # 1) VALIDACIÓN DATOS PROYECTO
    # -----------------------------------------------------
    try:
        validar_datos_proyecto(datos_proyecto or {})
    except Exception as e:
        warnings.append(f"validar_datos_proyecto: {e}")

    # -----------------------------------------------------
    # 2) USAR ESTRUCTURAS (YA LIMPIAS)
    # -----------------------------------------------------
    df_norm = estructuras_df

    if df_norm is None or df_norm.empty:
        warnings.append("No hay estructuras para procesar.")
        return ResultadoMateriales(
            df_materiales=_df_vacio(),
            df_materiales_detalle=_df_vacio(),
            errores=errores,
            warnings=warnings,
        )

    # -----------------------------------------------------
    # 3) CÁLCULO PRINCIPAL
    # -----------------------------------------------------
    try:
        resultado_calc = calcular_materiales_proyecto(
            df_estructuras=df_norm,
            hojas_base=hojas_base,
            tension=float(tension) if tension is not None else None,
        )
    except Exception as e:
        errores.append(f"Error en cálculo de materiales: {e}")
        return ResultadoMateriales(
            df_materiales=_df_vacio(),
            df_materiales_detalle=_df_vacio(),
            errores=errores,
            warnings=warnings,
        )

    # -----------------------------------------------------
    # 4) EXTRAER RESULTADOS
    # -----------------------------------------------------
    df_materiales = None
    df_detalle = None

    if isinstance(resultado_calc, dict):
        df_materiales = resultado_calc.get("df_materiales")
        df_detalle = resultado_calc.get("df_materiales_detalle")

    elif isinstance(resultado_calc, tuple):
        if len(resultado_calc) >= 1:
            df_materiales = resultado_calc[0]
        if len(resultado_calc) >= 2:
            df_detalle = resultado_calc[1]

    if df_materiales is None:
        df_materiales = _df_vacio()

    if df_detalle is None:
        df_detalle = _df_vacio()

    # -----------------------------------------------------
    # 5) INTEGRAR CABLES
    # -----------------------------------------------------
    if isinstance(df_cables, pd.DataFrame) and not df_cables.empty:
        try:
            from materiales.cables.cables_materiales import materiales_desde_cables

            df_cab = materiales_desde_cables(df_cables)
            df_materiales = _merge_materiales(df_materiales, df_cab)

        except Exception as e:
            warnings.append(f"Error integrando cables: {e}")

    # -----------------------------------------------------
    # 6) INTEGRAR MATERIALES EXTRA
    # -----------------------------------------------------
    if isinstance(df_materiales_extra, pd.DataFrame) and not df_materiales_extra.empty:
        try:
            df_materiales = _merge_materiales(df_materiales, df_materiales_extra)
        except Exception as e:
            warnings.append(f"Error integrando materiales extra: {e}")

    # -----------------------------------------------------
    # 7) RESULTADO FINAL
    # -----------------------------------------------------
    try:
        resultado = ResultadoMateriales(
            df_materiales=df_materiales,
            df_materiales_detalle=df_detalle,
            errores=errores,
            warnings=warnings,
        )

    except Exception as e:
        errores.append(f"Error construyendo ResultadoMateriales: {e}")
        resultado = ResultadoMateriales(
            df_materiales=_df_vacio(),
            df_materiales_detalle=_df_vacio(),
            errores=errores,
            warnings=warnings,
        )

    return resultado
