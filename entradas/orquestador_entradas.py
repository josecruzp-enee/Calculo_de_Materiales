# -*- coding: utf-8 -*-
from __future__ import annotations

# =========================================================
# IMPORTS
# =========================================================
import traceback
import pandas as pd
from typing import Any, Dict

# =========================================================
# CONTRATOS
# =========================================================
from interfaz.contratos import SalidaInterfaz, SalidaEntradas

# =========================================================
# LECTORES
# =========================================================
from entradas.leer_excel import leer_estructuras as leer_excel
from entradas.leer_tabla import leer_tabla
from entradas.leer_pdf import leer_pdf
from entradas.leer_dxf import leer_dxf

# =========================================================
# PROCESAMIENTO
# =========================================================
from entradas.normalizar import normalizar_estructuras
from entradas.validacion import validar_estructuras
from entradas.base_datos import cargar_base_datos


# =========================================================
# DISPATCH LECTURA
# =========================================================
def _leer(tipo: str, data: Any) -> pd.DataFrame:

    if tipo == "excel":
        return leer_excel(data)

    elif tipo == "tabla":
        return leer_tabla(data)

    elif tipo == "pdf":
        return leer_pdf(data)

    elif tipo == "dxf":
        return leer_dxf(data)

    elif tipo == "manual":
        return data

    else:
        raise ValueError(f"Tipo no soportado: {tipo}")


# =========================================================
# HELPERS DEBUG (TABLAS)
# =========================================================
def _safe_df_info(df: Any):
    if isinstance(df, pd.DataFrame):
        return df.head(10)  # 🔥 tabla real
    return pd.DataFrame({"valor": [str(type(df))]})


# =========================================================
# ORQUESTADOR ENTRADAS
# =========================================================
def ejecutar_entradas(
    entrada: SalidaInterfaz,
) -> SalidaEntradas:

    # =====================================================
    # DEBUG BASE (TABLA)
    # =====================================================
    debug: Dict[str, Any] = {
        "input": pd.DataFrame({
            "campo": ["tipo_entrada", "tiene_data", "tipo_data"],
            "valor": [
                entrada.tipo_entrada,
                entrada.data_entrada is not None,
                str(type(entrada.data_entrada))
            ]
        })
    }

    # =====================================================
    # VALIDACIÓN INTERFAZ
    # =====================================================
    if not entrada.ok:
        debug["estado"] = pd.DataFrame({
            "ok": [False],
            "origen": ["interfaz"],
            "errores": [str(entrada.errores)]
        })

        return SalidaEntradas(
            ok=False,
            errores=entrada.errores,
            warnings=entrada.warnings,
            debug=debug
        )

    try:
        # =====================================================
        # 1. LECTURA
        # =====================================================
        df_raw = _leer(entrada.tipo_entrada, entrada.data_entrada)

        debug["lectura"] = _safe_df_info(df_raw)

        if df_raw is None or getattr(df_raw, "empty", True):
            debug["estado"] = pd.DataFrame({
                "ok": [False],
                "fase": ["lectura"],
                "error": ["df_raw vacío o inválido"]
            })

            return SalidaEntradas(
                ok=False,
                errores=["No se pudo leer la entrada"],
                warnings=[],
                debug=debug
            )

        # =====================================================
        # 2. NORMALIZACIÓN
        # =====================================================
        df_norm, errores_norm, warnings_norm = normalizar_estructuras(df_raw)

        debug["normalizacion_df"] = _safe_df_info(df_norm)

        debug["normalizacion_info"] = pd.DataFrame({
            "errores": [str(errores_norm)],
            "warnings": [str(warnings_norm)]
        })

        if errores_norm:
            debug["estado"] = pd.DataFrame({
                "ok": [False],
                "fase": ["normalizacion"]
            })

            return SalidaEntradas(
                ok=False,
                errores=errores_norm,
                warnings=warnings_norm,
                debug=debug
            )

        # =====================================================
        # 3. VALIDACIÓN
        # =====================================================
        errores_val = validar_estructuras(df_norm)

        debug["validacion"] = pd.DataFrame({
            "errores": [str(errores_val)]
        })

        if errores_val:
            debug["estado"] = pd.DataFrame({
                "ok": [False],
                "fase": ["validacion"]
            })

            return SalidaEntradas(
                ok=False,
                errores=errores_val,
                warnings=warnings_norm,
                df_estructuras=df_norm,
                debug=debug
            )

        # =====================================================
        # 4. BASE DE DATOS
        # =====================================================
        base_datos = cargar_base_datos()

        debug["base_datos"] = pd.DataFrame({
            "hojas": list(base_datos.keys())
        })

        # =====================================================
        # 5. OUTPUT FINAL
        # =====================================================
        debug["output"] = _safe_df_info(df_norm)

        debug["estado"] = pd.DataFrame({
            "ok": [True]
        })

        return SalidaEntradas(
            ok=True,
            errores=[],
            warnings=warnings_norm,

            # CORE
            df_estructuras=df_norm,
            base_datos=base_datos,

            # CONTEXTO
            datos_proyecto=entrada.datos_proyecto,
            df_cables=entrada.df_cables,
            df_materiales_extra=entrada.df_materiales_extra,

            # DEBUG
            debug=debug
        )

    except Exception as e:

        debug["estado"] = pd.DataFrame({
            "ok": [False],
            "fase": ["exception"],
            "error": [str(e)]
        })

        debug["trace"] = pd.DataFrame({
            "trace": [traceback.format_exc()]
        })

        return SalidaEntradas(
            ok=False,
            errores=[str(e)],
            warnings=[],
            debug=debug
        )
