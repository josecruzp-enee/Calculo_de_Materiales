# -*- coding: utf-8 -*-
# entradas/orquestador_entradas.py

from __future__ import annotations

import pandas as pd

# =========================
# LECTURA
# =========================
from entradas.leer_excel import leer_estructuras
from entradas.leer_tabla import leer_tabla
from entradas.leer_pdf import leer_pdf
from entradas.leer_dxf import leer_dxf

# =========================
# PROCESAMIENTO
# =========================
from entradas.normalizar import normalizar_estructuras
from entradas.validacion import validar_estructuras
from entradas.indice_estructuras import cargar_indice_normalizado

# =========================
# CONTRATOS
# =========================
from entradas.contratos import EntradaEstructuras


# =========================================================
# ORQUESTADOR PRINCIPAL
# =========================================================

def cargar_entrada(
    tipo: str,
    data,
    ruta_materiales: str | None = None,
    *,
    permitir_sin_catalogo: bool = False,
) -> EntradaEstructuras:
    """
    Punto único de entrada del sistema.

    Flujo:
        1. Lectura
        2. Normalización
        3. Validación
        4. Salida

    Parámetros:
        tipo: "excel" | "tabla" | "pdf" | "dxf" | "ui"
        data: archivo, dataframe o estructura cruda
        ruta_materiales: ruta al catálogo de estructuras
        permitir_sin_catalogo: solo para debug

    Retorna:
        EntradaEstructuras
    """

    log = _get_logger()

    log(f"📥 Tipo de entrada: {tipo}")

    # =====================================================
    # 1. LECTURA
    # =====================================================
    df = _leer_por_tipo(tipo, data)

    if df is None or df.empty:
        raise ValueError("No se pudo leer información válida de la entrada")

    log(f"✔ Lectura completada: {len(df)} filas")

    # =====================================================
    # 2. NORMALIZACIÓN
    # =====================================================
    try:
        df = normalizar_estructuras(df)
    except Exception as e:
        raise ValueError(f"Error en normalización ({tipo}): {str(e)}")

    if df is None or df.empty:
        raise ValueError("La normalización generó un DataFrame vacío")

    log("✔ Normalización completada")

    # =====================================================
    # 3. VALIDACIÓN
    # =====================================================
    warnings = []
    errores = []

    if not ruta_materiales and not permitir_sin_catalogo:
        raise ValueError("Se requiere catálogo de materiales para validar estructuras")

    if ruta_materiales:
        df_indice = cargar_indice_normalizado(ruta_materiales, log)

        df, errores, warnings = validar_estructuras(df, df_indice, log)

        log(f"✔ Validación completada | warnings: {len(warnings)}")

    else:
        log("⚠ Validación omitida (modo debug)")

    if errores:
        raise ValueError("Errores en estructuras:\n" + "\n".join(errores))

    # =====================================================
    # 4. SALIDA
    # =====================================================
    return EntradaEstructuras(
        df=df,
        origen=tipo,
        warnings=warnings,
    )


# =========================================================
# LECTOR CENTRALIZADO
# =========================================================

def _leer_por_tipo(tipo: str, data) -> pd.DataFrame:

    if tipo == "excel":
        return leer_estructuras(data)

    elif tipo == "tabla":
        return leer_tabla(data)

    elif tipo == "pdf":
        return leer_pdf(data)

    elif tipo == "dxf":
        return leer_dxf(data)

    elif tipo == "ui":
        return _leer_desde_ui(data)

    raise ValueError(f"Tipo de entrada no soportado: {tipo}")


# =========================================================
# ADAPTADOR UI
# =========================================================

def _leer_desde_ui(data):

    if isinstance(data, pd.DataFrame):
        return data.copy()

    if isinstance(data, list):
        return pd.DataFrame(data)

    if isinstance(data, dict):
        return pd.DataFrame([data])

    return pd.DataFrame()


# =========================================================
# LOGGER (DESACOPLADO)
# =========================================================

def _get_logger():
    def _log(msg):
        print(msg)
    return _log
