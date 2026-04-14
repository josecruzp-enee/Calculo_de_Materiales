# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass


# =========================================================
# CONTRATO DE SALIDA
# =========================================================
@dataclass(slots=True)
class ResultadoCostosOperativos:
    """
    Costos operativos UNITARIOS (por estructura)
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
    costo_material_total: float,
    costo_mano_obra: float,
    factor_equipos: float = 0.05,
    factor_logistica: float = 0.15,
) -> ResultadoCostosOperativos:

    # =========================
    # VALIDACIONES
    # =========================
    for nombre, valor in {
        "costo_material_total": costo_material_total,
        "costo_mano_obra": costo_mano_obra,
        "factor_equipos": factor_equipos,
        "factor_logistica": factor_logistica,
    }.items():
        if not isinstance(valor, (int, float)):
            raise TypeError(f"{nombre} debe ser numérico")

    if costo_material_total < 0:
        raise ValueError("costo_material_total inválido")

    if costo_mano_obra < 0:
        raise ValueError("costo_mano_obra inválido")

    # =========================
    # CÁLCULO
    # =========================
    equipos = costo_material_total * factor_equipos
    logistica = costo_material_total * factor_logistica

    operativo_total = costo_mano_obra + equipos + logistica

    # =========================
    # OUTPUT
    # =========================
    return ResultadoCostosOperativos(
        mano_obra=round(costo_mano_obra, 2),
        equipos=round(equipos, 2),
        logistica=round(logistica, 2),
        operativo_total=round(operativo_total, 2),
    )
