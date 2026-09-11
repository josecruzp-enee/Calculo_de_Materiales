# -*- coding: utf-8 -*-
"""
costos_precios/costos_operativos.py

MODELO INTERNO DE PRODUCTIVIDAD Y COSTO DE EJECUCIÓN.

OBJETIVO
--------
Estimar el costo real de ejecución de un proyecto a partir de:

    estructuras
        ↓
    productividad
        ↓
    horas-cuadrilla / horas-equipo
        ↓
    duración
        ↓
    costos de ejecución

El mismo modelo físico servirá posteriormente para construir
el cronograma del proyecto y analizar el margen del contratista.

MODELO
------
Para cada estructura:

    Horas cuadrilla =
        cantidad × horas cuadrilla por unidad

    Horas equipo =
        cantidad × horas equipo por unidad

Para el proyecto:

    Duración =
        horas cuadrilla totales
        / (horas jornada × número de cuadrillas)

    Mano de obra =
        horas cuadrilla × costo cuadrilla por hora

    Equipos =
        suma(horas equipo × costo equipo por hora)

    Logística =
        días de ejecución × costo logística por día

    Costo ejecución =
        mano de obra + equipos + logística

    Utilidad =
        precio contratista - costo ejecución

    Margen % =
        utilidad / precio contratista × 100

IMPORTANTE
----------
Este módulo calcula COSTOS INTERNOS DE EJECUCIÓN.

NO calcula:
    - precio del contratista,
    - precio de venta,
    - ISV,
    - costo de materiales,
    - cotización comercial.

Las tarifas de contratistas se mantienen separadas.

ALIMENTA / USO PREVISTO
-----------------------
    - análisis interno de costos,
    - productividad,
    - duración del proyecto,
    - cronograma,
    - análisis de margen,
    - reporte completo de costos.

NOTA
----
Por ahora el catálogo de productividad se mantiene en este
mismo archivo. Cuando el modelo esté maduro podrá separarse.
"""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Real
from typing import Dict, Optional

import pandas as pd


# ==========================================================
# CONFIGURACIÓN GENERAL
# ==========================================================

HORAS_JORNADA_DEFAULT = 8.0
NUMERO_CUADRILLAS_DEFAULT = 1

COSTO_CUADRILLA_HORA_DEFAULT = 0.0
COSTO_LOGISTICA_DIA_DEFAULT = 0.0


# ==========================================================
# CATÁLOGO DE PRODUCTIVIDAD
# ==========================================================
#
# NO colocar rendimientos inventados.
#
# Estos valores deben calibrarse con experiencia de campo.
#
# Formato:
#
# "CODIGO": {
#     "horas_unidad": 0.0,
#     "horas_equipo_unidad": 0.0,
#     "costo_equipo_hora": 0.0,
# }
#
# horas_unidad:
#     Horas-cuadrilla necesarias para ejecutar una unidad.
#
# horas_equipo_unidad:
#     Horas de equipo necesarias para ejecutar una unidad.
#
# costo_equipo_hora:
#     Costo horario del equipo utilizado.
#
# ==========================================================

PRODUCTIVIDAD_ESTRUCTURAS: Dict[str, Dict[str, float]] = {}


# ==========================================================
# CONTRATOS DE SALIDA
# ==========================================================

@dataclass(slots=True)
class ResultadoEjecucion:
    """Resultado físico y económico de ejecución."""

    horas_cuadrilla: float
    horas_equipo: float
    dias_estimados: float

    mano_obra: float
    equipos: float
    logistica: float

    costo_ejecucion: float


@dataclass(slots=True)
class ResultadoMargen:
    """Comparación entre precio contratado y costo interno."""

    precio_contratista: float
    costo_ejecucion: float
    utilidad_bruta: float
    margen_porcentaje: float


# ==========================================================
# VALIDACIONES
# ==========================================================

def _numero_no_negativo(nombre: str, valor: float) -> float:
    """Valida número >= 0."""

    if isinstance(valor, bool) or not isinstance(valor, Real):
        raise TypeError(f"{nombre} debe ser numérico")

    valor = float(valor)

    if valor < 0:
        raise ValueError(f"{nombre} no puede ser negativo")

    return valor


def _numero_positivo(nombre: str, valor: float) -> float:
    """Valida número > 0."""

    valor = _numero_no_negativo(nombre, valor)

    if valor <= 0:
        raise ValueError(f"{nombre} debe ser mayor que cero")

    return valor


# ==========================================================
# PREPARACIÓN DE ESTRUCTURAS
# ==========================================================

def _normalizar_estructuras(
    df_estructuras: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normaliza estructuras.

    Acepta cualquiera de estas columnas para el código:

        CODIGO
        Estructura
        codigodeestructura

    Devuelve:
        CODIGO
        Cantidad
    """

    if not isinstance(df_estructuras, pd.DataFrame) or df_estructuras.empty:
        raise ValueError("df_estructuras vacío o inválido")

    df = df_estructuras.copy()

    if "CODIGO" not in df.columns:

        if "Estructura" in df.columns:
            df["CODIGO"] = df["Estructura"]

        elif "codigodeestructura" in df.columns:
            df["CODIGO"] = df["codigodeestructura"]

        else:
            raise ValueError(
                "No existe columna CODIGO, "
                "Estructura o codigodeestructura"
            )

    if "Cantidad" not in df.columns:
        raise ValueError("Falta columna Cantidad")

    df["CODIGO"] = (
        df["CODIGO"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["Cantidad"] = (
        pd.to_numeric(df["Cantidad"], errors="coerce")
        .fillna(0.0)
    )

    df = df[
        (df["CODIGO"] != "")
        & (df["Cantidad"] > 0)
    ]

    if df.empty:
        raise ValueError("No existen estructuras válidas")

    return (
        df.groupby("CODIGO", as_index=False)["Cantidad"]
        .sum()
    )


# ==========================================================
# PRODUCTIVIDAD
# ==========================================================

def obtener_productividad(
    codigo: str,
    catalogo: Optional[Dict[str, Dict[str, float]]] = None,
) -> Optional[Dict[str, float]]:
    """
    Obtiene los parámetros de productividad de una estructura.

    Devuelve None si la estructura todavía no está parametrizada.
    """

    catalogo = (
        PRODUCTIVIDAD_ESTRUCTURAS
        if catalogo is None
        else catalogo
    )

    codigo = str(codigo).strip().upper()

    datos = catalogo.get(codigo)

    if datos is None:
        return None

    return dict(datos)


def calcular_productividad_proyecto(
    df_estructuras: pd.DataFrame,
    *,
    catalogo: Optional[Dict[str, Dict[str, float]]] = None,
) -> pd.DataFrame:
    """
    Calcula productividad por estructura.

    Devuelve:
        CODIGO
        Cantidad
        Horas Unitarias
        Horas Cuadrilla
        Horas Equipo Unitarias
        Horas Equipo
        Costo Equipo Hora
        Costo Equipo
        Estado
    """

    df = _normalizar_estructuras(df_estructuras)

    filas = []

    for row in df.itertuples(index=False):

        codigo = str(row.CODIGO)
        cantidad = float(row.Cantidad)

        productividad = obtener_productividad(
            codigo,
            catalogo,
        )

        if productividad is None:

            filas.append({
                "CODIGO": codigo,
                "Cantidad": cantidad,
                "Horas Unitarias": 0.0,
                "Horas Cuadrilla": 0.0,
                "Horas Equipo Unitarias": 0.0,
                "Horas Equipo": 0.0,
                "Costo Equipo Hora": 0.0,
                "Costo Equipo": 0.0,
                "Estado": "SIN PRODUCTIVIDAD",
            })

            continue

        horas_unidad = _numero_no_negativo(
            f"{codigo}.horas_unidad",
            productividad.get("horas_unidad", 0.0),
        )

        horas_equipo_unidad = _numero_no_negativo(
            f"{codigo}.horas_equipo_unidad",
            productividad.get("horas_equipo_unidad", 0.0),
        )

        costo_equipo_hora = _numero_no_negativo(
            f"{codigo}.costo_equipo_hora",
            productividad.get("costo_equipo_hora", 0.0),
        )

        horas_cuadrilla = cantidad * horas_unidad
        horas_equipo = cantidad * horas_equipo_unidad
        costo_equipo = horas_equipo * costo_equipo_hora

        filas.append({
            "CODIGO": codigo,
            "Cantidad": round(cantidad, 2),
            "Horas Unitarias": round(horas_unidad, 2),
            "Horas Cuadrilla": round(horas_cuadrilla, 2),
            "Horas Equipo Unitarias": round(horas_equipo_unidad, 2),
            "Horas Equipo": round(horas_equipo, 2),
            "Costo Equipo Hora": round(costo_equipo_hora, 2),
            "Costo Equipo": round(costo_equipo, 2),
            "Estado": "OK",
        })

    return pd.DataFrame(filas)


# ==========================================================
# CONTROL DE PRODUCTIVIDAD
# ==========================================================

def obtener_estructuras_sin_productividad(
    df_productividad: pd.DataFrame,
) -> list[str]:
    """Devuelve las estructuras pendientes de parametrizar."""

    if not isinstance(df_productividad, pd.DataFrame):
        return []

    if df_productividad.empty:
        return []

    if not {"CODIGO", "Estado"}.issubset(df_productividad.columns):
        return []

    mask = df_productividad["Estado"] != "OK"

    return (
        df_productividad.loc[mask, "CODIGO"]
        .astype(str)
        .tolist()
    )


# ==========================================================
# DURACIÓN
# ==========================================================

def calcular_duracion_dias(
    horas_cuadrilla: float,
    *,
    horas_jornada: float = HORAS_JORNADA_DEFAULT,
    numero_cuadrillas: int = NUMERO_CUADRILLAS_DEFAULT,
) -> float:
    """
    Calcula duración agregada.

    duración =
        horas-cuadrilla
        -------------------------------
        horas/jornada × nº cuadrillas
    """

    horas_cuadrilla = _numero_no_negativo(
        "horas_cuadrilla",
        horas_cuadrilla,
    )

    horas_jornada = _numero_positivo(
        "horas_jornada",
        horas_jornada,
    )

    numero_cuadrillas = _numero_positivo(
        "numero_cuadrillas",
        numero_cuadrillas,
    )

    capacidad_diaria = (
        horas_jornada
        * numero_cuadrillas
    )

    return round(
        horas_cuadrilla / capacidad_diaria,
        2,
    )


# ==========================================================
# COSTO DE MANO DE OBRA
# ==========================================================

def calcular_costo_mano_obra(
    horas_cuadrilla: float,
    *,
    costo_cuadrilla_hora: float,
) -> float:
    """
    Calcula costo interno de mano de obra.

    MO =
        horas-cuadrilla × costo cuadrilla/hora
    """

    horas_cuadrilla = _numero_no_negativo(
        "horas_cuadrilla",
        horas_cuadrilla,
    )

    costo_cuadrilla_hora = _numero_no_negativo(
        "costo_cuadrilla_hora",
        costo_cuadrilla_hora,
    )

    return round(
        horas_cuadrilla * costo_cuadrilla_hora,
        2,
    )


# ==========================================================
# COSTO DE LOGÍSTICA
# ==========================================================

def calcular_costo_logistica(
    dias_estimados: float,
    *,
    costo_logistica_dia: float,
) -> float:
    """
    Calcula logística según duración.

    Logística =
        días × costo logístico diario
    """

    dias_estimados = _numero_no_negativo(
        "dias_estimados",
        dias_estimados,
    )

    costo_logistica_dia = _numero_no_negativo(
        "costo_logistica_dia",
        costo_logistica_dia,
    )

    return round(
        dias_estimados * costo_logistica_dia,
        2,
    )


# ==========================================================
# COSTO TOTAL DE EJECUCIÓN
# ==========================================================

def calcular_ejecucion(
    *,
    df_estructuras: pd.DataFrame,
    costo_cuadrilla_hora: float = COSTO_CUADRILLA_HORA_DEFAULT,
    costo_logistica_dia: float = COSTO_LOGISTICA_DIA_DEFAULT,
    horas_jornada: float = HORAS_JORNADA_DEFAULT,
    numero_cuadrillas: int = NUMERO_CUADRILLAS_DEFAULT,
    catalogo_productividad: Optional[
        Dict[str, Dict[str, float]]
    ] = None,
    exigir_productividad_completa: bool = True,
) -> tuple[ResultadoEjecucion, pd.DataFrame]:
    """
    Función principal del modelo.

    Calcula simultáneamente:

        productividad,
        horas-cuadrilla,
        horas-equipo,
        duración,
        mano de obra,
        equipos,
        logística,
        costo total de ejecución.

    Retorna:
        resultado
        df_productividad
    """

    costo_cuadrilla_hora = _numero_no_negativo(
        "costo_cuadrilla_hora",
        costo_cuadrilla_hora,
    )

    costo_logistica_dia = _numero_no_negativo(
        "costo_logistica_dia",
        costo_logistica_dia,
    )

    horas_jornada = _numero_positivo(
        "horas_jornada",
        horas_jornada,
    )

    numero_cuadrillas = _numero_positivo(
        "numero_cuadrillas",
        numero_cuadrillas,
    )

    # ------------------------------------------------------
    # Productividad
    # ------------------------------------------------------

    df_prod = calcular_productividad_proyecto(
        df_estructuras,
        catalogo=catalogo_productividad,
    )

    faltantes = obtener_estructuras_sin_productividad(
        df_prod
    )

    if faltantes and exigir_productividad_completa:
        raise ValueError(
            "Falta productividad para: "
            + ", ".join(sorted(faltantes))
        )

    df_ok = df_prod[
        df_prod["Estado"] == "OK"
    ].copy()

    # ------------------------------------------------------
    # Horas
    # ------------------------------------------------------

    horas_cuadrilla = float(
        df_ok["Horas Cuadrilla"].sum()
    )

    horas_equipo = float(
        df_ok["Horas Equipo"].sum()
    )

    # ------------------------------------------------------
    # Duración
    # ------------------------------------------------------

    dias_estimados = calcular_duracion_dias(
        horas_cuadrilla,
        horas_jornada=horas_jornada,
        numero_cuadrillas=numero_cuadrillas,
    )

    # ------------------------------------------------------
    # Mano de obra
    # ------------------------------------------------------

    costo_mano_obra = calcular_costo_mano_obra(
        horas_cuadrilla,
        costo_cuadrilla_hora=costo_cuadrilla_hora,
    )

    # ------------------------------------------------------
    # Equipos
    # ------------------------------------------------------

    costo_equipos = float(
        df_ok["Costo Equipo"].sum()
    )

    # ------------------------------------------------------
    # Logística
    # ------------------------------------------------------

    costo_logistica = calcular_costo_logistica(
        dias_estimados,
        costo_logistica_dia=costo_logistica_dia,
    )

    # ------------------------------------------------------
    # Total
    # ------------------------------------------------------

    costo_ejecucion = (
        costo_mano_obra
        + costo_equipos
        + costo_logistica
    )

    resultado = ResultadoEjecucion(
        horas_cuadrilla=round(horas_cuadrilla, 2),
        horas_equipo=round(horas_equipo, 2),
        dias_estimados=round(dias_estimados, 2),

        mano_obra=round(costo_mano_obra, 2),
        equipos=round(costo_equipos, 2),
        logistica=round(costo_logistica, 2),

        costo_ejecucion=round(costo_ejecucion, 2),
    )

    return resultado, df_prod


# ==========================================================
# ANÁLISIS DE MARGEN
# ==========================================================

def calcular_margen(
    *,
    precio_contratista: float,
    costo_ejecucion: float,
) -> ResultadoMargen:
    """
    Compara precio del contratista contra costo interno.

    utilidad =
        precio - costo

    margen =
        utilidad / precio × 100
    """

    precio_contratista = _numero_no_negativo(
        "precio_contratista",
        precio_contratista,
    )

    costo_ejecucion = _numero_no_negativo(
        "costo_ejecucion",
        costo_ejecucion,
    )

    utilidad = (
        precio_contratista
        - costo_ejecucion
    )

    margen = (
        utilidad / precio_contratista * 100
        if precio_contratista > 0
        else 0.0
    )

    return ResultadoMargen(
        precio_contratista=round(
            precio_contratista,
            2,
        ),
        costo_ejecucion=round(
            costo_ejecucion,
            2,
        ),
        utilidad_bruta=round(
            utilidad,
            2,
        ),
        margen_porcentaje=round(
            margen,
            2,
        ),
    )
