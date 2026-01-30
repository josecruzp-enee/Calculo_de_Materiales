# -*- coding: utf-8 -*-
"""
entradas_excel.py

Lectura de insumos desde Excel.
Devuelve estructuras crudas (dict/DataFrame) para las siguientes etapas del proceso.
"""

from __future__ import annotations

from typing import Dict, Optional, Any
import pandas as pd


def leer_hoja_excel(
    archivo_excel: str,
    *,
    hoja: str,
    header: Optional[int] = 0,
    usecols: Optional[Any] = None,
    nrows: Optional[int] = None,
) -> pd.DataFrame:
    """
    Lee una hoja de Excel y retorna el DataFrame.

    Parámetros:
        archivo_excel: ruta del archivo .xlsx
        hoja: nombre exacto de la hoja
        header: fila de encabezados (por defecto 0). Usa None si no hay encabezados.
        usecols: columnas a leer (opcional)
        nrows: filas a leer (opcional)

    Retorna:
        DataFrame
    """
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
            f"No se pudo leer la hoja '{hoja}' desde el archivo: {archivo_excel}. "
            f"Detalle: {e}"
        )


def leer_datos_proyecto_desde_excel(
    archivo_excel: str,
    *,
    hoja: str = "datos_proyecto",
    n_filas: int = 10,
) -> Dict[str, str]:
    """
    Lee la hoja 'datos_proyecto' como pares (clave, valor).

    Espera:
        - Dos columnas (col 0 = clave, col 1 = valor)

    Retorna:
        dict[str, str]
    """
    df = leer_hoja_excel(
        archivo_excel,
        hoja=hoja,
        header=0,
        usecols=[0, 1],
        nrows=n_filas,
    )

    salida: Dict[str, str] = {}
    for k, v in df.values:
        if pd.isna(k):
            continue
        clave = str(k).strip().lower().replace(":", "")
        valor = "" if pd.isna(v) else str(v).strip()
        if clave:
            salida[clave] = valor

    return salida


def leer_estructuras_desde_excel(
    archivo_excel: str,
    *,
    hoja: str = "estructuras",
) -> pd.DataFrame:
    """
    Lee la hoja 'estructuras' y retorna el DataFrame.
    """
    return leer_hoja_excel(archivo_excel, hoja=hoja, header=0)


def leer_materiales_adicionales_desde_excel(
    archivo_excel: str,
    *,
    hoja: str = "materialesadicionados",
) -> pd.DataFrame:
    """
    Lee la hoja 'materialesadicionados' y retorna el DataFrame.
    """
    return leer_hoja_excel(archivo_excel, hoja=hoja, header=0)


def leer_hoja_generica_desde_excel(
    archivo_excel: str,
    *,
    hoja: str,
    header: Optional[int] = None,
) -> pd.DataFrame:
    """
    Lectura genérica de cualquier hoja (útil para hojas por estructura u otras tablas).
    """
    return leer_hoja_excel(archivo_excel, hoja=hoja, header=header)

