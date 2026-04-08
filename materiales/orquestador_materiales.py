# -*- coding: utf-8 -*-
# materiales/orquestador_materiales.py

from __future__ import annotations

from typing import Optional, Dict, Any, List
import pandas as pd
from entradas.base_datos import cargar_base_datos

# =========================================================
# CONTRATO OFICIAL
# =========================================================
from interfaz.contratos import ResultadoMateriales

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

from materiales.calculos.calculo_estructuras import (
    calcular_estructuras_proyecto
)

# =========================================================
# DEBUG
# =========================================================
from ayuda.debug import debug_guardar


# =========================================================
# HELPERS DEBUG
# =========================================================
def _debug(etapa: str, nombre: str, valor):
    debug_guardar(f"{etapa}::{nombre}", valor)


def _check(etapa: str, nombre: str, condicion: bool, detalle=None):
    debug_guardar(f"CHECK::{etapa}::{nombre}", {
        "ok": bool(condicion),
        "detalle": str(detalle)[:200]
    })


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
    # 1. INPUT
    # =====================================================
    df_norm = entrada.estructuras_df
    hojas_base = cargar_base_datos()
    tension = entrada.tension
    df_cables = entrada.df_cables
    df_materiales_extra = entrada.df_materiales_extra

    _debug("INPUT", "df_estructuras", df_norm)
    _debug("INPUT", "tension", tension)
    _debug("INPUT", "df_cables", df_cables)
    _debug("INPUT", "df_materiales_extra", df_materiales_extra)

    _check("INPUT", "df_valido",
        isinstance(df_norm, pd.DataFrame) and not df_norm.empty,
        getattr(df_norm, "shape", None)
    )

    _check("INPUT", "hojas_base_ok",
        isinstance(hojas_base, dict) and len(hojas_base) > 0,
        type(hojas_base).__name__
    )

    # =====================================================
    # 2. VALIDACIÓN
    # =====================================================
    try:
        validar_datos_proyecto({})
    except Exception as e:
        warnings.append(f"validar_datos_proyecto: {e}")
        _debug("VALIDACION", "warning_validacion", str(e))

    if df_norm is None or df_norm.empty:
        warnings.append("No hay estructuras para procesar.")

        _debug("VALIDACION", "sin_estructuras", True)

        return SalidaMateriales(
            ok=True,
            errores=errores,
            warnings=warnings,
            df_materiales=_df_vacio(),
            df_materiales_por_punto=_df_vacio(),
            debug=debug
        )

    # =====================================================
    # 3. PRE CÁLCULO
    # =====================================================
    _debug("PRE", "n_estructuras", len(df_norm))
    _debug("PRE", "columnas", list(df_norm.columns))

    if "Estructura" in df_norm.columns:
        estructuras = df_norm["Estructura"].dropna().unique().tolist()
        _debug("PRE", "estructuras_unicas", estructuras[:50])

    # =====================================================
    # 4. CÁLCULO PRINCIPAL
    # =====================================================
    try:
        resultado_calc = calcular_materiales_proyecto(
            df_estructuras=df_norm,
            hojas_base=hojas_base,
            tension=float(tension) if tension is not None else None,
        )

        _debug("CALCULO", "resultado_raw", resultado_calc)

    except Exception as e:
        errores.append(f"Error en cálculo de materiales: {e}")

        _debug("ERROR", "calculo", str(e))

        return SalidaMateriales(
            ok=False,
            errores=errores,
            warnings=warnings,
            df_materiales=_df_vacio(),
            df_materiales_por_punto=_df_vacio(),
            debug=debug
        )

    # =====================================================
    # 4.1 CÁLCULO DE ESTRUCTURAS (NUEVO)
    # =====================================================
    try:
        resultado_estructuras = calcular_estructuras_proyecto(df_norm)

        df_estructuras = resultado_estructuras.get("df_estructuras")
        df_estructuras_por_punto = resultado_estructuras.get("df_estructuras_por_punto")
        descripcion_estructuras = resultado_estructuras.get("descripcion_por_punto")

        _debug("ESTRUCTURAS", "global", df_estructuras)
        _debug("ESTRUCTURAS", "por_punto", df_estructuras_por_punto)

    except Exception as e:
        warnings.append(f"Error en cálculo de estructuras: {e}")
        _debug("ERROR", "estructuras", str(e))

        df_estructuras = None
        df_estructuras_por_punto = None
        descripcion_estructuras = {}
    
    # =====================================================
    # 5. EXTRAER RESULTADOS
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

    _check("POST", "df_materiales_existe", df_materiales is not None)
    _check("POST", "df_detalle_existe", df_detalle is not None)

    if df_materiales is None:
        df_materiales = _df_vacio()

    if df_detalle is None:
        df_detalle = _df_vacio()

    _debug("POST", "df_materiales", df_materiales)
    _debug("POST", "df_detalle", df_detalle)

    # =====================================================
    # 6. CABLES
    # =====================================================
    if isinstance(df_cables, pd.DataFrame) and not df_cables.empty:
        try:
            from materiales.cables.cables_materiales import materiales_desde_cables
            df_cab = materiales_desde_cables(df_cables)

            _debug("CABLES", "df_cables_convertido", df_cab)

            df_materiales = _merge_materiales(df_materiales, df_cab)

        except Exception as e:
            warnings.append(f"Error integrando cables: {e}")
            _debug("ERROR", "cables", str(e))

    # =====================================================
    # 7. MATERIALES EXTRA
    # =====================================================
    if isinstance(df_materiales_extra, pd.DataFrame) and not df_materiales_extra.empty:
        try:
            _debug("EXTRA", "df_materiales_extra", df_materiales_extra)

            df_materiales = _merge_materiales(df_materiales, df_materiales_extra)

        except Exception as e:
            warnings.append(f"Error integrando materiales extra: {e}")
            _debug("ERROR", "materiales_extra", str(e))

    # =====================================================
    # 8. OUTPUT FINAL
    # =====================================================
    _debug("OUTPUT", "filas_final", len(df_materiales))
    _debug("OUTPUT", "columnas_final", list(df_materiales.columns))

    return ResultadoMateriales(
        ok=True,
        errores=errores,
        warnings=warnings,
        df_estructuras=df_estructuras,
        df_estructuras_por_punto=df_estructuras_por_punto,
        descripcion_estructuras=descripcion_estructuras,
        df_materiales=df_materiales,
        df_materiales_por_punto=df_detalle,
        datos_proyecto=entrada.datos_proyecto,
        debug=debug
    )
