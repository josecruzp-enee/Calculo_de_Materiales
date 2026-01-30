# -*- coding: utf-8 -*-
"""
entradas_excel.py

Lectura SOLO de estructuras desde Excel.
Devuelve la tabla ANCHA tal como viene en el archivo para que la siguiente etapa
la normalice y convierta a formato LARGO (si aplica).
"""

from __future__ import annotations

from typing import Optional, Any
import pandas as pd


def leer_hoja_excel(
    archivo_excel: Any,
    *,
    hoja: str,
    header: Optional[int] = 0,
    usecols: Optional[Any] = None,
    nrows: Optional[int] = None,
) -> pd.DataFrame:
    try:
        return pd.read_excel(
            archivo_excel,
            sheet_name=hoja,
            header=header,
            usecols=usecols,
            nrows=nrows,
        )
    except Exception as e:
        raise ValueError(
            f"No se pudo leer la hoja '{hoja}' desde el archivo. Detalle: {e}"
        )


def leer_estructuras_desde_excel(
    archivo_excel: Any,
    *,
    hoja: str = "estructuras",
) -> pd.DataFrame:
    """
    Lee la hoja 'estructuras' y retorna el DataFrame ANCHO.
    (Punto, Poste, Primario, Secundario, Retenida, Aterrizaje, Transformador)
    """
    return leer_hoja_excel(archivo_excel, hoja=hoja, header=0)
