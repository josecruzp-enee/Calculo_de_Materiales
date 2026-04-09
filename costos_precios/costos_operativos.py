# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass


# =========================================================
# CONTRATO DE SALIDA
# =========================================================
@dataclass(slots=True)
class ResultadoCostosOperativos:
    """
    Todos los valores en moneda local (L)
    """
    mano_obra: float
    equipos: float
    logistica: float
    operativo_total: float


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================
def calcular_costos_operativos(
    *,
    costo_cuadrilla_dia: float,
    fraccion_jornada: float = 1/16,
    costo_equipos: float = 0.0,
    costo_logistica: float = 0.0,
) -> ResultadoCostosOperativos:
    """
    Calcula costos operativos:

    ✔ Mano de obra
    ✔ Equipos/herramientas
    ✔ Logística

    Dominio puro:
    - Sin efectos secundarios
    - Contrato fuerte
    - Determinista
    """

    # =====================================================
    # VALIDACIÓN TIPOS
    # =====================================================
    for nombre, valor in {
        "costo_cuadrilla_dia": costo_cuadrilla_dia,
        "fraccion_jornada": fraccion_jornada,
        "costo_equipos": costo_equipos,
        "costo_logistica": costo_logistica,
    }.items():
        if not isinstance(valor, (int, float)):
            raise TypeError(f"{nombre} debe ser numérico")

    # =====================================================
    # VALIDACIÓN VALORES
    # =====================================================
    if costo_cuadrilla_dia <= 0:
        raise ValueError("costo_cuadrilla_dia debe ser > 0")

    if not (0 < fraccion_jornada <= 1):
        raise ValueError("fraccion_jornada debe estar en (0, 1]")

    if costo_equipos < 0:
        raise ValueError("costo_equipos no puede ser negativo")

    if costo_logistica < 0:
        raise ValueError("costo_logistica no puede ser negativo")

    # =====================================================
    # CÁLCULOS
    # =====================================================
    mano_obra = float(costo_cuadrilla_dia) * float(fraccion_jornada)
    equipos = float(costo_equipos)
    logistica = float(costo_logistica)

    operativo_total = mano_obra + equipos + logistica

    # =====================================================
    # OUTPUT (REDONDEO CONTROLADO)
    # =====================================================
    return ResultadoCostosOperativos(
        mano_obra=round(mano_obra, 2),
        equipos=round(equipos, 2),
        logistica=round(logistica, 2),
        operativo_total=round(operativo_total, 2),
    )
