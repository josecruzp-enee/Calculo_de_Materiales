# -*- coding: utf-8 -*-
"""
costos_precios/costos_mano_obra.py

MODELO PARAMÉTRICO DE COSTO DE EJECUCIÓN DE MANO DE OBRA.

ROL:
    Estimar internamente el costo de ejecución de las estructuras
    mediante factores paramétricos.

OBJETIVO:
    Este módulo NO representa el precio cobrado por un contratista.
    Su propósito es servir como modelo interno para estimar cuánto
    debería costar ejecutar físicamente el proyecto.

DIFERENCIA IMPORTANTE:

    costos_mano_obra.py
        → COSTO INTERNO ESTIMADO DE EJECUCIÓN

    mano_obra_por_punto.py
        → PRECIO / TARIFA COBRADA POR EL CONTRATISTA

MODELO ACTUAL:
    MO_unitaria =
        MO_base
        × factor_fases
        × factor_tipo
        × factor_geometrico

    MO_total =
        MO_unitaria
        × cantidad
        × factor_escala

FUENTE ACTUAL DEL COSTO BASE:
    Hoja "indice" del archivo de materiales.

    Columnas requeridas:
        CODIGO
        PRECIO

    Columna opcional:
        DESCRIPCION

ALIMENTA / USO FUTURO:
    Este módulo está destinado a alimentar:

    - Análisis interno de costo de ejecución.
    - Comparación costo interno vs. precio del contratista.
    - Estimación del margen bruto del contratista.
    - Modelo de productividad por estructura.
    - Estimación de horas-cuadrilla.
    - Cronograma de ejecución del proyecto.
    - Reporte completo de costos.

    IMPORTANTE:
    Estos usos representan la arquitectura objetivo.
    Antes de asumir que están activos debe verificarse la conexión
    correspondiente en el orquestador del sistema.

NO ALIMENTA DIRECTAMENTE:
    - PDF de contratista.
    - Cotización comercial al cliente.

NO HACE:
    - No genera PDF.
    - No calcula materiales.
    - No calcula ISV.
    - No calcula precio de venta.
    - No utiliza las tarifas C1/C2.
    - No debe contener precios específicos de contratistas.

EVOLUCIÓN PREVISTA:
    El modelo actual basado en factores puede evolucionar hacia
    un modelo de productividad basado en:

        cantidad
        × horas por unidad
        × costo horario de cuadrilla

    incorporando posteriormente:
        - composición de cuadrilla,
        - salarios/cargas,
        - equipos,
        - transporte,
        - productividad,
        - jornadas,
        - duración estimada.

NOTA:
    Los factores actuales se conservan por compatibilidad.
    Deben validarse antes de utilizar este módulo como modelo
    definitivo de costo real de ejecución.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Tuple

import pandas as pd

from ayuda.debug import debug_guardar


# ==========================================================
# DEBUG
# ==========================================================

def _debug(etapa: str, info: Dict[str, Any]) -> None:
    """Registra información de diagnóstico del modelo."""
    debug_guardar("MANO_OBRA", etapa, info)


# ==========================================================
# FACTORES PARAMÉTRICOS
# ==========================================================

def obtener_fases_desde_codigo(codigo: str) -> int:
    """Obtiene el número de fases indicado por el código."""

    cod = str(codigo).upper()
    match = re.search(r"-([IVX]+)-", cod)

    if not match:
        return 1

    return {
        "I": 1,
        "II": 2,
        "III": 3,
    }.get(match.group(1), 1)


def obtener_factor_fases(fases: int) -> float:
    """Factor asociado al número de fases."""

    return {
        1: 1.00,
        2: 1.50,
        3: 2.00,
    }.get(fases, 1.00)


def obtener_factor_tipo(codigo: str) -> float:
    """Factor asociado al tipo general de estructura."""

    cod = str(codigo).strip().upper()

    if not cod:
        return 1.00

    if cod.startswith("CT"):
        return 1.10

    if cod.startswith("LL"):
        return 0.75

    if cod.startswith("CA"):
        return 0.80

    if cod.startswith(("TS", "T")):
        return 1.80

    return {
        "P": 1.50,
        "A": 1.25,
        "B": 1.00,
        "C": 1.20,
        "R": 1.30,
    }.get(cod[0], 1.00)


def obtener_factor_geometrico(codigo: str) -> float:
    """Factor asociado a la configuración geométrica del código."""

    cod = str(codigo).strip().upper()
    match = re.search(r"-(\d+)$", cod)

    if not match:
        return 1.00

    numero = int(match.group(1))

    return {
        1: 1.00,
        2: 1.15,
        4: 1.30,
        5: 1.40,
        6: 1.60,
    }.get(numero, 1.00)


def obtener_factor_escala(cantidad: int) -> float:
    """
    Factor de economía de escala.

    Reduce el costo unitario estimado cuando aumenta
    la cantidad de estructuras iguales.
    """

    if cantidad <= 4:
        return 1.00

    if cantidad <= 9:
        return 0.93

    if cantidad <= 19:
        return 0.88

    return 0.82


# ==========================================================
# PREPARACIÓN DE ENTRADA
# ==========================================================

def _validar_entrada(df: pd.DataFrame) -> None:
    """Valida el DataFrame de estructuras."""

    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("df_estructuras vacío o inválido")

    requeridas = {"CODIGO", "Cantidad"}
    faltantes = requeridas - set(df.columns)

    if faltantes:
        raise ValueError(
            f"df_estructuras sin columnas requeridas: "
            f"{sorted(faltantes)}"
        )


def _normalizar_entrada(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza códigos y cantidades."""

    df = df.copy()

    df["CODIGO"] = (
        df["CODIGO"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["Cantidad"] = (
        pd.to_numeric(df["Cantidad"], errors="coerce")
        .fillna(0)
    )

    return df


def _agrupar_por_codigo(df: pd.DataFrame) -> pd.DataFrame:
    """Consolida cantidades repetidas de una misma estructura."""

    return (
        df.groupby("CODIGO", as_index=False)["Cantidad"]
        .sum()
    )


# ==========================================================
# LECTURA DEL ÍNDICE
# ==========================================================

def _leer_indice(
    archivo_materiales: str,
) -> Tuple[Dict[str, float], Dict[str, str]]:
    """
    Lee precio base y descripción desde la hoja 'indice'.

    PRECIO representa actualmente el costo base utilizado
    por el modelo paramétrico.
    """

    df_indice = pd.read_excel(
        archivo_materiales,
        sheet_name="indice",
    )

    df_indice.columns = [
        str(c).strip().upper()
        for c in df_indice.columns
    ]

    requeridas = {"CODIGO", "PRECIO"}
    faltantes = requeridas - set(df_indice.columns)

    if faltantes:
        raise ValueError(
            f"Hoja 'indice' sin columnas requeridas: "
            f"{sorted(faltantes)}"
        )

    if "DESCRIPCION" not in df_indice.columns:
        df_indice["DESCRIPCION"] = ""

    df_indice["CODIGO"] = (
        df_indice["CODIGO"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df_indice["PRECIO"] = (
        pd.to_numeric(
            df_indice["PRECIO"],
            errors="coerce",
        )
        .fillna(0.0)
    )

    precio_map = dict(
        zip(
            df_indice["CODIGO"],
            df_indice["PRECIO"],
        )
    )

    desc_map = dict(
        zip(
            df_indice["CODIGO"],
            df_indice["DESCRIPCION"].astype(str),
        )
    )

    return precio_map, desc_map


# ==========================================================
# CÁLCULO UNITARIO
# ==========================================================

def _calcular_fila(
    cod: str,
    qty: int,
    precio_map: Dict[str, float],
    desc_map: Dict[str, str],
):
    """
    Calcula el costo paramétrico de una estructura.

    MO_unit =
        MO_base
        × factor_fases
        × factor_tipo
        × factor_geometrico

    MO_total =
        MO_unit
        × cantidad
        × factor_escala
    """

    if cod not in precio_map:
        return None, f"{cod}: sin costo base"

    mo_base = float(precio_map[cod])

    if mo_base <= 0:
        return None, f"{cod}: costo base inválido"

    fases = obtener_fases_desde_codigo(cod)

    f_fases = obtener_factor_fases(fases)
    f_tipo = obtener_factor_tipo(cod)
    f_geom = obtener_factor_geometrico(cod)
    f_escala = obtener_factor_escala(qty)

    mo_unit = (
        mo_base
        * f_fases
        * f_tipo
        * f_geom
    )

    mo_total = (
        mo_unit
        * qty
        * f_escala
    )

    fila = {
        "CODIGO": cod,
        "Descripcion": desc_map.get(cod, ""),
        "Cantidad": qty,
        "MO Base": round(mo_base, 2),
        "Fases": fases,
        "Factor Fases": f_fases,
        "Factor Tipo": f_tipo,
        "Factor Geometrico": f_geom,
        "Factor Escala": f_escala,
        "MO Unitario Ajustado": round(mo_unit, 2),
        "MO Total": round(mo_total, 2),
    }

    return fila, None


# ==========================================================
# FUNCIÓN PRINCIPAL
# ==========================================================

def calcular_mano_obra(
    *,
    df_estructuras: pd.DataFrame,
    archivo_materiales: str,
) -> pd.DataFrame:
    """
    Calcula el costo paramétrico estimado de ejecución.

    SALIDA:
        DataFrame con:

        CODIGO
        Descripcion
        Cantidad
        MO Base
        Fases
        Factor Fases
        Factor Tipo
        Factor Geometrico
        Factor Escala
        MO Unitario Ajustado
        MO Total

    IMPORTANTE:
        El resultado representa COSTO INTERNO ESTIMADO.

        No debe interpretarse como tarifa o precio
        comercial de un contratista.
    """

    _validar_entrada(df_estructuras)

    df = _normalizar_entrada(df_estructuras)
    df_group = _agrupar_por_codigo(df)

    precio_map, desc_map = _leer_indice(
        archivo_materiales
    )

    filas = []
    errores = []

    for _, row in df_group.iterrows():

        cod = row["CODIGO"]
        qty = int(row["Cantidad"])

        if qty <= 0:
            continue

        fila, error = _calcular_fila(
            cod,
            qty,
            precio_map,
            desc_map,
        )

        if error:
            errores.append(error)
            continue

        filas.append(fila)

    df_out = pd.DataFrame(filas)

    if df_out.empty:

        _debug(
            "ERROR",
            {
                "errores": errores,
            },
        )

        raise ValueError(
            "No se generó costo paramétrico de mano de obra"
        )

    total_mo = float(
        df_out["MO Total"].sum()
    )

    _debug(
        "RESULTADO",
        {
            "filas": len(df_out),
            "total_mo": total_mo,
            "errores": errores,
        },
    )

    return df_out
