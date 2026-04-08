# costos/costos_operativos.py

from __future__ import annotations


def calcular_costos_operativos(
    *,
    costo_cuadrilla_dia: float,
    fraccion_jornada: float = 1/16,
    costo_equipos: float = 0.0,
    costo_logistica: float = 0.0,
) -> dict:
    """
    Calcula:
    Mano de obra + equipos/herramientas + logística

    Parámetros:
    - costo_cuadrilla_dia: costo de la cuadrilla por día (L/día)
    - fraccion_jornada: fracción de día usada (default 1/16)
    - costo_equipos: costo directo de equipos/herramientas
    - costo_logistica: transporte, viáticos, etc.

    Retorna dict estructurado
    """

    # -------------------------
    # VALIDACIONES
    # -------------------------
    if costo_cuadrilla_dia <= 0:
        raise ValueError("costo_cuadrilla_dia inválido")

    if fraccion_jornada <= 0:
        raise ValueError("fraccion_jornada inválida")

    if costo_equipos < 0 or costo_logistica < 0:
        raise ValueError("costos negativos no permitidos")

    # -------------------------
    # MANO DE OBRA
    # -------------------------
    mano_obra = costo_cuadrilla_dia * fraccion_jornada

    # -------------------------
    # TOTAL OPERATIVO
    # -------------------------
    total_operativo = mano_obra + costo_equipos + costo_logistica

    return {
        "mano_obra": round(mano_obra, 2),
        "equipos": round(costo_equipos, 2),
        "logistica": round(costo_logistica, 2),
        "operativo_total": round(total_operativo, 2),
    }
