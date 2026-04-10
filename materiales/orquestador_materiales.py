# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional, Dict, Any, List
import pandas as pd

# =========================================================
# CONTRATO OFICIAL
# =========================================================
from materiales.modelos.salida import SalidaMateriales

# =========================================================
# MODELOS
# =========================================================
from materiales.modelos.entrada import EntradaMateriales

# =========================================================
# CÁLCULO
# =========================================================
from materiales.calculos.calculo_materiales import (calcular_materiales_proyecto)
from materiales.calculos.materiales_puntos import (
    calcular_materiales_por_estructura,
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

    debug: Dict[str, Any] = {
        "input": {
            "filas_estructuras": len(entrada.estructuras_df)
            if isinstance(entrada.estructuras_df, pd.DataFrame) else 0,
            "columnas_estructuras": list(entrada.estructuras_df.columns)
            if isinstance(entrada.estructuras_df, pd.DataFrame) else [],
            "tension": entrada.tension,
            "tiene_materiales_extra": isinstance(entrada.df_materiales_extra, pd.DataFrame),
        }
    }

    df_norm = entrada.estructuras_df
    hojas_base = entrada.base_datos
    tension = entrada.tension
    df_materiales_extra = entrada.df_materiales_extra
    datos = entrada.datos_proyecto or {}

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    if df_norm is None or df_norm.empty:

        debug["estado"] = {
            "ok": True,
            "warning": "sin estructuras"
        }

        return SalidaMateriales(
            ok=True,
            errores=[],
            warnings=["No hay estructuras para procesar."],
            df_materiales=_df_vacio(),
            df_materiales_por_punto=_df_vacio(),
            datos_proyecto=entrada.datos_proyecto,
            debug=debug
        )

    # =====================================================
    # 1. CÁLCULO MATERIALES
    # =====================================================
    try:
        resultado_calc = calcular_materiales_proyecto(
            df_estructuras=df_norm,
            hojas_base=hojas_base,
            tension=float(tension) if tension is not None else None,
        )

        debug["calculo_materiales"] = {
            "tipo_resultado": str(type(resultado_calc))
        }

        debug["calc_keys"] = list(resultado_calc.keys()) if isinstance(resultado_calc, dict) else "no_dict"

    except Exception as e:

        debug["estado"] = {
            "ok": False,
            "fase": "calculo_materiales",
            "error": str(e)
        }

        return SalidaMateriales(
            ok=False,
            errores=[f"Error en cálculo de materiales: {e}"],
            warnings=[],
            df_materiales=_df_vacio(),
            df_materiales_por_punto=_df_vacio(),
            datos_proyecto=entrada.datos_proyecto,
            debug=debug
        )

    # =====================================================
    # 🔥 NUEVO: MATERIALES POR ESTRUCTURA
    # =====================================================
    materiales_por_estructura = calcular_materiales_por_estructura(
        hojas_base=hojas_base,
        df_estructuras=df_norm,
        tension=tension,
        calibre_mt=entrada.calibre_mt,
        tabla_conectores_mt=entrada.tabla_conectores_mt,
    )

    debug["materiales_por_estructura"] = {
        "total": len(materiales_por_estructura)
    }

    # =====================================================
    # 2. CÁLCULO ESTRUCTURAS
    # =====================================================
    try:
        resultado_estructuras = calcular_estructuras_proyecto(df_norm)

        df_estructuras = resultado_estructuras.get("df_estructuras")
        df_estructuras_por_punto = resultado_estructuras.get("df_estructuras_por_punto")

        debug["calculo_estructuras"] = {
            "filas": len(df_estructuras) if isinstance(df_estructuras, pd.DataFrame) else 0
        }

    except Exception as e:

        warnings.append(f"Error en cálculo de estructuras: {e}")

        debug["calculo_estructuras"] = {
            "error": str(e)
        }

        df_estructuras = None
        df_estructuras_por_punto = None

    # =====================================================
    # 3. EXTRAER RESULTADOS
    # =====================================================
    df_materiales = None
    df_detalle = None

    if isinstance(resultado_calc, dict):
        df_materiales = resultado_calc.get("df_materiales")
        df_detalle = resultado_calc.get("df_materiales_por_punto")

    elif isinstance(resultado_calc, tuple):
        df_materiales = resultado_calc[0] if len(resultado_calc) >= 1 else None
        df_detalle = resultado_calc[1] if len(resultado_calc) >= 2 else None

    debug["raw_materiales"] = {
        "df_materiales_none": df_materiales is None,
        "df_detalle_none": df_detalle is None,
    }

    if df_materiales is None:
        df_materiales = _df_vacio()

    if df_detalle is None:
        df_detalle = _df_vacio()

    debug["post_procesado"] = {
        "materiales": len(df_materiales),
        "detalle": len(df_detalle),
    }

    # =====================================================
    # 4. MATERIALES EXTRA
    # =====================================================
    if isinstance(df_materiales_extra, pd.DataFrame) and not df_materiales_extra.empty:
        try:
            df_materiales = _merge_materiales(df_materiales, df_materiales_extra)
        except Exception as e:
            warnings.append(f"Error integrando materiales extra: {e}")

    # =====================================================
    # 5. OUTPUT FINAL
    # =====================================================
    return SalidaMateriales(
        ok=True,
        errores=[],
        warnings=warnings,
        df_materiales=df_materiales,
        df_materiales_por_punto=df_detalle,
        df_estructuras=df_estructuras,
        df_estructuras_por_punto=df_estructuras_por_punto,

        # 🔥 AQUÍ ESTÁ LA CLAVE
        descripcion_estructuras=materiales_por_estructura,

        datos_proyecto=entrada.datos_proyecto,
        debug=debug
    )
