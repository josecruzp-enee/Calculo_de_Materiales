# entradas/base_datos.py

import pandas as pd


def cargar_base_datos(ruta_archivo: str) -> dict:
    """
    Carga TODO el Excel y devuelve un diccionario:
    {nombre_hoja: DataFrame}
    """

    xls = pd.ExcelFile(ruta_archivo)

    hojas = {}

    for hoja in xls.sheet_names:
        hojas[hoja] = pd.read_excel(xls, sheet_name=hoja)

    return hojas
