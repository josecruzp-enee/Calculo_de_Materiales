# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd


# ==========================================================
# CONFIGURACIÓN BASE (BIBLIOTECA)
# ==========================================================
COSTOS_BASE = {
    "poste": 2000,
    "primario": 1500,
    "secundario": 1000,
    "luminaria": 500,
}

FACTOR_FASES = {
    "A-I": 1.0,
    "A-II": 1.3,
    "A-III": 1.6,
}

FACTOR_COMPLEJIDAD = {
    "PASO": 1.0,
    "ANGULO": 1.2,
    "DOBLE": 1.4,
    "REMATE": 1.6,
}


# ==========================================================
# DETECTORES
# ==========================================================
def _detectar_componentes(estructuras: list[str]) -> dict:

    return {
        "poste": any(e.startswith("PC") for e in estructuras),
        "primario": any(e.startswith("A-") for e in estructuras),
        "secundario": any(e.startswith("B-") for e in estructuras),
        "luminaria": any(e.startswith("LL") for e in estructuras),
        "transformador": [e for e in estructuras if e.startswith("TS")],
    }


def _detectar_fases(estructuras: list[str]) -> float:

    for e in estructuras:
        if e.startswith("A-III"):
            return FACTOR_FASES["A-III"]
        if e.startswith("A-II"):
            return FACTOR_FASES["A-II"]

    return FACTOR_FASES["A-I"]


def _detectar_complejidad(estructuras: list[str]) -> float:
    """
    Placeholder simple.
    Aquí luego puedes integrar tu lógica de ángulos.
    """

    for e in estructuras:
        if "REM" in e:
            return FACTOR_COMPLEJIDAD["REMATE"]
        if "DOB" in e:
            return FACTOR_COMPLEJIDAD["DOBLE"]

    return FACTOR_COMPLEJIDAD["PASO"]


# ==========================================================
# TRANSFORMADOR
# ==========================================================
def _costo_transformador(estructuras: list[str], precios_transformador: dict) -> float:

    total = 0

    for e in estructuras:
        if e in precios_transformador:
            total += precios_transformador[e] * 0.5

    return total


# ==========================================================
# CÁLCULO POR PUNTO
# ==========================================================
def calcular_mano_obra_punto(
    df_estructuras_por_punto: pd.DataFrame,
    precios_transformador: dict,
) -> pd.DataFrame:

    if df_estructuras_por_punto is None or df_estructuras_por_punto.empty:
        return pd.DataFrame(columns=["Punto", "MANO_OBRA"])

    resultados = []

    for punto in sorted(df_estructuras_por_punto["Punto"].unique()):

        df_p = df_estructuras_por_punto[df_estructuras_por_punto["Punto"] == punto]

        estructuras = df_p["Estructura"].tolist()

        comp = _detectar_componentes(estructuras)

        fases = _detectar_fases(estructuras)
        complejidad = _detectar_complejidad(estructuras)

        total = 0

        # Poste
        if comp["poste"]:
            total += COSTOS_BASE["poste"]

        # Primario
        if comp["primario"]:
            total += COSTOS_BASE["primario"] * fases * complejidad

        # Secundario
        if comp["secundario"]:
            total += COSTOS_BASE["secundario"] * complejidad

        # Luminaria
        if comp["luminaria"]:
            total += COSTOS_BASE["luminaria"]

        # Transformador
        total += _costo_transformador(estructuras, precios_transformador)

        resultados.append({
            "Punto": punto,
            "MANO_OBRA": round(total, 2)
        })

    return pd.DataFrame(resultados)
