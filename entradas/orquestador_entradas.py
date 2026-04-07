# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

# =========================================================
# CONTRATOS
# =========================================================
from interfaz.contratos import SalidaInterfaz, SalidaEntradas

# =========================================================
# LECTORES
# =========================================================
from entradas.leer_excel import leer_estructuras
from entradas.leer_tabla import leer_tabla
from entradas.leer_pdf import leer_pdf
from entradas.leer_dxf import leer_dxf

# =========================================================
# PROCESAMIENTO
# =========================================================
from entradas.normalizar import normalizar_estructuras
from entradas.validacion import validar_estructuras
from entradas.indice_estructuras import cargar_indice_normalizado
from entradas.base_datos import obtener_ruta_base


# =========================================================
# ORQUESTADOR PRINCIPAL
# =========================================================
def ejecutar_entradas(
    entrada: SalidaInterfaz,
    *,
    tension: float,
    validar_catalogo: bool = True,
) -> SalidaEntradas:

    debug = {}
    errores = []
    warnings = []

    # =====================================================
    # 0. VALIDACIÓN INTERFAZ
    # =====================================================
    if not entrada.ok:
        return _error("Entrada de interfaz inválida", debug, extra=entrada.errores)

    tipo = entrada.tipo_entrada
    data = entrada.data_entrada

    debug["input"] = {
        "tipo": tipo,
        "data_type": type(data).__name__
    }

    # =====================================================
    # 1. LECTURA
    # =====================================================
    df_raw = _leer(tipo, data, debug)
    if _vacio(df_raw):
        return _error("Lectura vacía", debug)

    # =====================================================
    # 2. NORMALIZACIÓN
    # =====================================================
    df_norm, err, warn = _normalizar(df_raw, debug)
    if err:
        return _error(err, debug)
    warnings.extend(warn)

    # =====================================================
    # 3. VALIDACIÓN ESTRUCTURAL
    # =====================================================
    err = _validar_estructura(df_norm)
    if err:
        return _error(err, debug)

    # =====================================================
    # 4. VALIDACIÓN CATÁLOGO
    # =====================================================
    df_final, err, warn = _validar_catalogo(
        df_norm,
        validar_catalogo,
        debug
    )
    if err:
        return _error(err, debug)
    warnings.extend(warn)

    # =====================================================
    # 5. SALIDA
    # =====================================================
    return SalidaEntradas(
        ok=True,
        errores=[],
        warnings=warnings,
        df_estructuras=df_final,
        datos_proyecto=entrada.datos_proyecto,
        df_cables=entrada.df_cables,
        df_materiales_extra=entrada.df_materiales_extra,
        debug=debug
    )


# =========================================================
# 🔷 LECTURA
# =========================================================
def _leer(tipo, data, debug):

    try:
        if tipo == "excel":
            df = leer_estructuras(data)

        elif tipo == "tabla":
            df = leer_tabla(data)

        elif tipo == "pdf":
            df = leer_pdf(data)

        elif tipo == "dxf":
            df = leer_dxf(data)

        elif tipo == "manual":
            df = _leer_ui(data)

        else:
            return None

        debug["df_raw"] = _resumen(df)
        return df

    except Exception as e:
        debug["error_lectura"] = str(e)
        return None


# =========================================================
# 🔷 NORMALIZACIÓN
# =========================================================
def _normalizar(df, debug):

    try:
        df_norm, errores, warnings = normalizar_estructuras(df)

        debug["df_norm"] = _resumen(df_norm)

        if errores:
            return None, "\n".join(errores), []

        return df_norm, None, warnings or []

    except Exception as e:
        return None, str(e), []


# =========================================================
# 🔷 VALIDACIÓN ESTRUCTURAL
# =========================================================
def _validar_estructura(df):

    if df is None:
        return "DataFrame nulo"

    if "codigodeestructura" not in df.columns:
        return "Falta codigodeestructura"

    invalidos = df["codigodeestructura"].astype(str).str.contains(" ")

    if invalidos.any():
        ejemplos = df.loc[invalidos, "codigodeestructura"].unique()[:5]
        return "Estructuras mal parseadas:\n" + "\n".join(ejemplos)

    return None


# =========================================================
# 🔷 VALIDACIÓN CATÁLOGO
# =========================================================
def _validar_catalogo(df, activar, debug):

    if not activar:
        return df, None, []

    try:
        ruta = obtener_ruta_base()
        df_indice = cargar_indice_normalizado(ruta)

        df_val, errores, warnings = validar_estructuras(df, df_indice)

        if errores:
            return None, "\n".join(errores), []

        debug["df_validado"] = _resumen(df_val)

        return df_val, None, warnings or []

    except Exception as e:
        return None, str(e), []


# =========================================================
# 🔷 HELPERS
# =========================================================
def _leer_ui(data):

    if isinstance(data, pd.DataFrame):
        return data.copy()

    if isinstance(data, list):
        return pd.DataFrame(data)

    if isinstance(data, dict):
        return pd.DataFrame([data])

    return None


def _vacio(df):
    return df is None or not hasattr(df, "empty") or df.empty


def _resumen(df):
    if df is None:
        return None
    return {
        "filas": df.shape[0],
        "columnas": list(df.columns)
    }


def _error(msg, debug, extra=None):

    errores = [msg]

    if extra:
        errores.extend(extra if isinstance(extra, list) else [extra])

    return SalidaEntradas(
        ok=False,
        errores=errores,
        warnings=[],
        df_estructuras=pd.DataFrame(),
        debug=debug
    )
