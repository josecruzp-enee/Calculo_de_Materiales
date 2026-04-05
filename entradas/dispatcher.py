# -*- coding: utf-8 -*-
# entradas/dispatcher.py

from typing import Optional
import pandas as pd

from .excel import cargar_excel
from .tabla import pegar_tabla
from .pdf import cargar_pdf
from .dxf import cargar_dxf


MAPA_MODOS = {
    "excel": cargar_excel,
    "tabla": pegar_tabla,
    "pdf": cargar_pdf,
    "dxf": cargar_dxf,
}


def ejecutar_entrada(modo: str, st) -> Optional[pd.DataFrame]:
    fn = MAPA_MODOS.get(modo)

    if not fn:
        raise ValueError(f"Modo no soportado: {modo}")

    return fn(st)
