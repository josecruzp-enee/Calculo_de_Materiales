# -*- coding: utf-8 -*-
"""
cables_catalogo.py
Catálogo oficial de cables (descripciones completas) y listas para UI.
"""

from __future__ import annotations
from typing import Dict, List, Tuple

# =========================
# Catálogo oficial (TU LISTA)
# =========================
CABLES_OFICIALES: Dict[Tuple[str, str], str] = {
    # Retenidas (acerado)
    ("RETENIDA", "1/4"):  'Cable Acerado 1/4"',
    ("RETENIDA", "5/16"): 'Cable Acerado 5/16"',
    ("RETENIDA", "3/8"):  'Cable Acerado 3/8"',

    # BT forrado WP (Quince/Fig/Peach)
    ("BT", "2 WP"):      "Cable de Aluminio Forrado WP # 2 AWG Peach",
    ("BT", "1/0 WP"):    "Cable de Aluminio Forrado WP # 1/0 AWG Quince",
    ("BT", "3/0 WP"):    "Cable de Aluminio Forrado WP # 3/0 AWG Fig",
    ("BT", "266.8 MCM"): "Cable de Aluminio Forrado 266.8 MCM Mulberry",

    # HP Hilo Piloto
    ("HP", "2 WP"):      "Cable de Aluminio Forrado WP # 2 AWG Peach",
    ("HP", "1/0 WP"):    "Cable de Aluminio Forrado WP # 1/0 AWG Quince",

    # Neutro (ACSR)
    ("N", "2 ACSR"):     "Cable de Aluminio ACSR # 2 AWG Sparrow",
    ("N", "1/0 ACSR"):   "Cable de Aluminio ACSR # 1/0 AWG Raven",
    ("N", "2/0 ACSR"):   "Cable de Aluminio ACSR # 2/0 AWG Quail",
    ("N", "3/0 ACSR"):   "Cable de Aluminio ACSR # 3/0 AWG Pigeon",
    ("N", "4/0 ACSR"):   "Cable de Aluminio ACSR # 4/0 AWG Penguin",

    # Media Tensión
    ("MT", "1/0 ACSR"):   "Cable de Aluminio ACSR # 1/0 AWG Raven",
    ("MT", "2/0 ACSR"):   "Cable de Aluminio ACSR # 2/0 AWG Quail",
    ("MT", "3/0 ACSR"):   "Cable de Aluminio ACSR # 3/0 AWG Pigeon",
    ("MT", "4/0 ACSR"):   "Cable de Aluminio ACSR # 4/0 AWG Penguin",
    ("MT", "266.8 MCM"):  "Cable de Aluminio ACSR # 266.8 MCM Partridge",
    ("MT", "477 MCM"):    "Cable de Aluminio ACSR # 477 MCM Flicker",
    ("MT", "556 MCM ACSR"): "Cable de Aluminio ACSR # 556 MCM Dove",
    ("MT", "556 MCM AAC"):  "Cable de Aluminio AAC # 556 MCM Dahlia",
}

# -----------------
# Listas para UI
# -----------------
def get_tipos() -> List[str]:
    # Lo que ve el usuario en la UI
    return ["MT", "BT", "N", "HP", "Retenida"]


def get_calibres() -> Dict[str, List[str]]:
    """
    Devuelve opciones de 'Calibre' como DESCRIPCIONES OFICIALES
    (tal como en tu script original).
    """
    return {
        "MT": [
            CABLES_OFICIALES[("MT", "1/0 ACSR")],
            CABLES_OFICIALES[("MT", "2/0 ACSR")],
            CABLES_OFICIALES[("MT", "3/0 ACSR")],
            CABLES_OFICIALES[("MT", "4/0 ACSR")],
            CABLES_OFICIALES[("MT", "266.8 MCM")],
            CABLES_OFICIALES[("MT", "477 MCM")],
            CABLES_OFICIALES[("MT", "556 MCM ACSR")],
            CABLES_OFICIALES[("MT", "556 MCM AAC")],
        ],
        "BT": [
            CABLES_OFICIALES[("BT", "2 WP")],
            CABLES_OFICIALES[("BT", "1/0 WP")],
            CABLES_OFICIALES[("BT", "3/0 WP")],
            CABLES_OFICIALES[("BT", "266.8 MCM")],
        ],
        "N": [
            CABLES_OFICIALES[("N", "2 ACSR")],
            CABLES_OFICIALES[("N", "1/0 ACSR")],
            CABLES_OFICIALES[("N", "2/0 ACSR")],
            CABLES_OFICIALES[("N", "3/0 ACSR")],
            CABLES_OFICIALES[("N", "4/0 ACSR")],
        ],
        "HP": [
            CABLES_OFICIALES[("HP", "2 WP")],
            CABLES_OFICIALES[("HP", "1/0 WP")],
        ],
        # En UI se llama "Retenida"
        "Retenida": [
            CABLES_OFICIALES[("RETENIDA", "1/4")],
            CABLES_OFICIALES[("RETENIDA", "5/16")],
            CABLES_OFICIALES[("RETENIDA", "3/8")],
        ],
        # Por compatibilidad si alguien usa "RETENIDA" como key interna
        "RETENIDA": [
            CABLES_OFICIALES[("RETENIDA", "1/4")],
            CABLES_OFICIALES[("RETENIDA", "5/16")],
            CABLES_OFICIALES[("RETENIDA", "3/8")],
        ],
    }


def get_calibres_union() -> List[str]:
    """
    Lista plana sin duplicados (manteniendo orden) para SelectboxColumn.
    """
    seen: List[str] = []
    for _, lst in get_calibres().items():
        for x in lst:
            if x not in seen:
                seen.append(x)
    return seen


def get_configs_por_tipo() -> Dict[str, List[str]]:
    """
    Configuraciones válidas por tipo.
    Mantengo tu lógica original:
      - MT: 1F/2F/3F
      - BT: 1F/2F
      - N : N
      - HP: 1F/2F
      - Retenida: Única
    """
    return {
        "MT": ["1F", "2F", "3F"],
        "BT": ["1F", "2F"],
        "N":  ["N"],
        "HP": ["1F", "2F"],
        "Retenida": ["Única"],
        "RETENIDA": ["Única"],
    }


def get_configs_union() -> List[str]:
    seen: List[str] = []
    for _, lst in get_configs_por_tipo().items():
        for x in lst:
            if x not in seen:
                seen.append(x)
    return seen
