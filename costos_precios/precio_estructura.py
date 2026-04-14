# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass


# =========================================================
# CONTRATO DE SALIDA
# =========================================================
@dataclass(slots=True)
class ResultadoPrecioEstructura:
    """
    Precio unitario completo por estructura
    """
    estructura: str
    costo_materiales: float
    costo_operativo: float
    costo_base: float
    utilidad: float
    precio_unitario: float


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================
# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================
def calcular_precio_estructura(
    *,
    estructura: str,
    costo_materiales: float,
    costo_operativo: float,
    porcentaje_utilidad: float,
) -> ResultadoPrecioEstructura:
    """
    Calcula el precio unitario por estructura.

    PRECIO = materiales + operación + utilidad

    Donde:
    operación = MO + equipos + logística
    """

    # =====================================================
    # VALIDACIONES
    # =====================================================
    if not isinstance(estructura, str) or not estructura.strip():
        raise ValueError("estructura inválida")

    for nombre, valor in {
        "costo_materiales": costo_materiales,
        "costo_operativo": costo_operativo,
        "porcentaje_utilidad": porcentaje_utilidad,
    }.items():
        if not isinstance(valor, (int, float)):
            raise TypeError(f"{nombre} debe ser numérico")

    if costo_materiales < 0:
        raise ValueError("costo_materiales no puede ser negativo")

    if costo_operativo < 0:
        raise ValueError("costo_operativo no puede ser negativo")

    if porcentaje_utilidad < 0:
        raise ValueError("porcentaje_utilidad no puede ser negativo")

    # =====================================================
    # CÁLCULO BASE
    # =====================================================
    costo_base = float(costo_materiales) + float(costo_operativo)

    # =====================================================
    # UTILIDAD
    # =====================================================
    utilidad = costo_base * float(porcentaje_utilidad)

    # =====================================================
    # PRECIO FINAL
    # =====================================================
    precio_unitario = costo_base + utilidad

    # =====================================================
    # OUTPUT
    # =====================================================
    return ResultadoPrecioEstructura(
        estructura=estructura.strip().upper(),
        costo_materiales=round(costo_materiales, 2),
        costo_operativo=round(costo_operativo, 2),
        costo_base=round(costo_base, 2),
        utilidad=round(utilidad, 2),
        precio_unitario=round(precio_unitario, 2),
    )
