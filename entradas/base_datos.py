# entradas/base_datos.py

import pandas as pd
from pathlib import Path


RUTA_BASE = Path(__file__).resolve().parent.parent / "data" / "Estructura_datos.xlsx"


def cargar_base_datos() -> dict:
    """
    Carga todas las hojas del Excel base.
    """

    xls = pd.ExcelFile(RUTA_BASE)

    hojas = {}

    for hoja in xls.sheet_names:
        hojas[hoja] = pd.read_excel(xls, sheet_name=hoja)

    return hojas
