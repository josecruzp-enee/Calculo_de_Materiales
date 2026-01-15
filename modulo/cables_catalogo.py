# -*- coding: utf-8 -*-
"""
cables_catalogo.py
Catálogos (tipos, calibres, configuraciones) para UI/validaciones.
"""

from __future__ import annotations
from typing import Dict, List


def get_tipos() -> List[str]:
    # mantené tus nombres aquí como los venís usando en la UI
    return ["MT", "BT", "N", "HP", "Retenida"]


def get_calibres() -> Dict[str, List[str]]:
    # Ajustá a tu lista real (la que ya tenías)
    return {
        "MT": ["2 ACSR", "1/0 ACSR", "2/0 ACSR", "3/0 ACSR", "4/0 ACSR", "266.8 MCM", "336 MCM"],
        "BT": ["2 WP", "1/0 WP", "2/0 WP", "3/0 WP", "4/0 WP"],
        "N":  ["2 ACSR", "1/0 ACSR", "2/0 ACSR", "3/0 ACSR", "4/0 ACSR"],
        "HP": ["2 WP", "1/0 WP", "2/0 WP"],
        "RETENIDA": ['1/4', '5/16', '3/8'],
        "Retenida": ['1/4', '5/16', '3/8'],  # por si tu UI usa "Retenida"
    }


def get_calibres_union() -> List[str]:
    seen = []
    for _, lst in get_calibres().items():
        for x in lst:
            if x not in seen:
                seen.append(x)
    return seen


def get_configs_por_tipo() -> Dict[str, List[str]]:
    # Si ya tenías esto, pegalo tal cual.
    # Si no, dejalo así y luego lo completas.
    return {
        "MT": ["1F", "2F", "3F"],
        "BT": ["1F", "2F", "3F"],
        "N":  ["N"],
        "HP": ["HP"],
        "Retenida": ["RET"],
        "RETENIDA": ["RET"],
    }


def get_configs_union() -> List[str]:
    seen = []
    for _, lst in get_configs_por_tipo().items():
        for x in lst:
            if x not in seen:
                seen.append(x)
    return seen
