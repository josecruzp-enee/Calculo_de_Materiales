# -*- coding: utf-8 -*-
# materiales/orquestador_materiales.py

from __future__ import annotations

from typing import Optional, Dict, Any, List
import pandas as pd

# =========================================================
# CONTRATO OFICIAL
# =========================================================
from interfaz.contratos import SalidaMateriales

# =========================================================
# MODELOS
# =========================================================
from materiales.modelos.entrada import EntradaMateriales

# =========================================================
# CÁLCULO
# =========================================================
from materiales.calculos.calculo_materiales import (
    calcular_materiales_proyecto,
)

from materiales.validaciones.materiales_validacion import (
    validar_datos_proyecto,
)


# =========================================================
# HELPERS
# =========================================================
def _df_vacio() -> pd.DataFrame:
    return pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])


def _merge_materiales(df_a, df_b):
    if df_a is None or df_a.empty:
        return df_b if isinstance(df_b, pd.DataFrame) else _df_vacio()

    if df_b is None or df_b.empty:
        return df_a

    df = pd.concat([df_a, df_b], ignore_index=True)

    if not set(["Materiales", "Unidad", "Cantidad"]).issubset(df.columns):
        return df

    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0.0)

    return (
        df.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"]
        .sum()
        .sort_values(["Materiales", "Unidad"])
        .reset_index(drop=True)
    )


# =========================================================
# ORQUESTADOR PRINCIPAL
# =========================================================
def ejecutar_materiales(
    entrada: EntradaMateriales,
    catalogo: Optional[Dict[str, Any]] = None,
) -> SalidaMateriales:

    errores: List[str] = []
    warnings: List[str] = []
    debug: Dict[str, Any] = {}

    # =====================================================
    # 1. EXTRAER DATOS
    # =====================================================
    df_norm = entrada.estructuras_df
    hojas_base = entrada.hojas_base
    tension = entrada.tension
    df_cables = entrada.df_cables
    df_materiales_extra = entrada.df_materiales_extra

    debug["entrada"] = {
        "estructuras_shape": None if df_norm is None else df_norm.shape,
        "tension": tension,
        "hojas_base": list(hojas_base.keys())[:5] if isinstance(hojas_base, dict) else None,
        "cables": None if df_cables is None else len(df_cables),
        "materiales_extra": None if df_materiales_extra is None else len(df_materiales_extra),
    }

    # =====================================================
    # 2. VALIDACIÓN
    # =====================================================
    try:
        validar_datos_proyecto({})
    except Exception as e:
        warnings.append(f"validar_datos_proyecto: {e}")

    if df_norm is None or df_norm.empty:
        warnings.append("No hay estructuras para procesar.")
        return SalidaMateriales(
            ok=True,
            errores=errores,
            warnings=warnings,
            df_materiales=_df_vacio(),
            df_materiales_por_punto=_df_vacio(),
            debug=debug
        )

    # =====================================================
    # 3. CÁLCULO PRINCIPAL
    # =====================================================
    try:
        resultado_calc = calcular_materiales_proyecto(
            df_estructuras=df_norm,
            hojas_base=hojas_base,
            tension=float(tension) if tension is not None else None,
        )
    except Exception as e:
        errores.append(f"Error en cálculo de materiales: {e}")
        return SalidaMateriales(
            ok=False,
            errores=errores,
            warnings=warnings,
            df_materiales=_df_vacio(),
            df_materiales_por_punto=_df_vacio(),
            debug=debug
        )

    # =====================================================
    # 4. EXTRAER RESULTADOS
    # =====================================================
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

    debug["post_calculo"] = {
        "materiales_rows": len(df_materiales),
        "detalle_rows": len(df_detalle),
    }

    # =====================================================
    # 5. CABLES
    # =====================================================
    if isinstance(df_cables, pd.DataFrame) and not df_cables.empty:
        try:
            from materiales.cables.cables_materiales import materiales_desde_cables
            df_cab = materiales_desde_cables(df_cables)
            df_materiales = _merge_materiales(df_materiales, df_cab)

        except Exception as e:
            warnings.append(f"Error integrando cables: {e}")

    # =====================================================
    # 6. MATERIALES EXTRA
    # =====================================================
    if isinstance(df_materiales_extra, pd.DataFrame) and not df_materiales_extra.empty:
        try:
            df_materiales = _merge_materiales(df_materiales, df_materiales_extra)
        except Exception as e:
            warnings.append(f"Error integrando materiales extra: {e}")

    # =====================================================
    # 7. RESULTADO FINAL
    # =====================================================
    return SalidaMateriales(
        ok=True,
        errores=errores,
        warnings=warnings,
        df_materiales=df_materiales,
        df_materiales_por_punto=df_detalle,
        datos_proyecto=entrada.datos_proyecto,
        debug=debug
    )
