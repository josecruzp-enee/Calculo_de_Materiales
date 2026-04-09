# -*- coding: utf-8 -*-
from __future__ import annotations

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
# DEBUG
# =========================================================
from ayuda.debug import debug_guardar
import pandas as pd


def _debug(etapa: str, nombre: str, valor):
    debug_guardar(f"{etapa}::{nombre}", valor)


def _check(etapa: str, nombre: str, condicion: bool, detalle=None):
    debug_guardar(f"CHECK::{etapa}::{nombre}", {
        "ok": bool(condicion),
        "detalle": str(detalle)[:200]
    })


# =========================================================
# DISPATCH
# =========================================================
def _leer(tipo: str, data):

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
# ORQUESTADOR REAL (PIPELINE)
# =========================================================
def ejecutar_entradas(
    entrada: SalidaInterfaz,
    *,
    tension: float,
    validar_catalogo: bool = True,
) -> SalidaEntradas:

    # =====================================================
    # DEBUG INICIAL
    # =====================================================
    _debug("INPUT", "tipo_entrada", entrada.tipo_entrada)
    _debug("INPUT", "data_entrada", entrada.data_entrada)
    _debug("INPUT", "datos_proyecto", entrada.datos_proyecto)
    _debug("INPUT", "df_cables", entrada.df_cables)
    _debug("INPUT", "df_materiales_extra", entrada.df_materiales_extra)

    # =====================================================
    # 1. VALIDACIÓN INTERFAZ
    # =====================================================
    _check("INTERFAZ", "entrada_ok", entrada.ok, entrada.errores)

    if not entrada.ok:
        return SalidaEntradas(
            ok=False,
            errores=entrada.errores,
            warnings=entrada.warnings,
            debug={"origen": "interfaz"}
        )

    try:
        # =====================================================
        # 2. LECTURA
        # =====================================================
        df_raw = _leer(entrada.tipo_entrada, entrada.data_entrada)

        _debug("LECTURA", "df_raw", df_raw)

        _check(
            "LECTURA",
            "df_raw_valido",
            isinstance(df_raw, pd.DataFrame) and not df_raw.empty,
            getattr(df_raw, "shape", None)
        )

        if df_raw is None or getattr(df_raw, "empty", True):
            return SalidaEntradas(
                ok=False,
                errores=["No se pudo leer la entrada"],
                debug={"fase": "lectura"}
            )

        # =====================================================
        # 3. NORMALIZACIÓN
        # =====================================================
        df_norm, errores_norm, warnings_norm = normalizar_estructuras(df_raw)

        _debug("NORMALIZACION", "df_norm", df_norm)
        _debug("NORMALIZACION", "errores_norm", errores_norm)
        _debug("NORMALIZACION", "warnings_norm", warnings_norm)

        _check(
            "NORMALIZACION",
            "df_norm_ok",
            isinstance(df_norm, pd.DataFrame),
            getattr(df_norm, "shape", None)
        )

        if isinstance(df_norm, pd.DataFrame):
            _check(
                "NORMALIZACION",
                "tiene_columna_estructura",
                "Estructura" in df_norm.columns,
                list(df_norm.columns)
            )

        if errores_norm:
            return SalidaEntradas(
                ok=False,
                errores=errores_norm,
                warnings=warnings_norm,
                debug={"fase": "normalizacion"}
            )

        # =====================================================
        # 4. VALIDACIÓN
        # =====================================================
        errores_val = validar_estructuras(df_norm)

        _debug("VALIDACION", "errores_val", errores_val)

        _check(
            "VALIDACION",
            "sin_errores",
            not bool(errores_val),
            errores_val
        )

        if errores_val:
            return SalidaEntradas(
                ok=False,
                errores=errores_val,
                warnings=warnings_norm,
                df_estructuras=df_norm,
                debug={"fase": "validacion"}
            )

        # =====================================================
        # 5. MÉTRICAS CLAVE
        # =====================================================
        estructuras_unicas = (
            df_norm["Estructura"].dropna().unique().tolist()
            if "Estructura" in df_norm.columns else []
        )

        _debug("OUTPUT", "filas", len(df_norm))
        _debug("OUTPUT", "columnas", list(df_norm.columns))
        _debug("OUTPUT", "estructuras_unicas", estructuras_unicas[:50])

        # =====================================================
        # 6. OK
        # =====================================================
        base_datos = cargar_base_datos()
        return SalidaEntradas(
            ok=True,
            errores=[],
            warnings=warnings_norm,
            df_estructuras=df_norm,
            datos_proyecto=entrada.datos_proyecto,
            df_cables=entrada.df_cables,
            df_materiales_extra=entrada.df_materiales_extra,
            base_datos=base_datos,
            debug={
                "fase": "ok",
                "filas": len(df_norm),
                "columnas": list(df_norm.columns),
                "tipo": entrada.tipo_entrada,
                "estructuras": len(estructuras_unicas)
            }
        )

    except Exception as e:

        _debug("EXCEPTION", "error", str(e))

        return SalidaEntradas(
            ok=False,
            errores=[str(e)],
            debug={
                "fase": "exception",
                "tipo": entrada.tipo_entrada
            }
        )
