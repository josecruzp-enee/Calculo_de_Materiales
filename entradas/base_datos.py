# -*- coding: utf-8 -*-

from __future__ import annotations

import pandas as pd
from pathlib import Path


# ==========================================================
# CONFIG
# ==========================================================
RUTA_BASE = Path(__file__).resolve().parent.parent / "data" / "Estructura_datos.xlsx"


# ==========================================================
# CARGA BASE DE DATOS
# ==========================================================
def cargar_base_datos() -> dict[str, pd.DataFrame]:
    """
    Carga todas las hojas del Excel en memoria.

    Retorna:
        dict[str, DataFrame]

    Clave:
        nombre de estructura normalizado (UPPER + strip)

    Valor:
        DataFrame de la hoja
    """

    if not RUTA_BASE.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {RUTA_BASE}")

    xls = pd.ExcelFile(RUTA_BASE)

    hojas: dict[str, pd.DataFrame] = {}

    for hoja in xls.sheet_names:

        # =========================
        # Leer hoja
        # =========================
        df = xls.parse(hoja)

        # =========================
        # Normalizar nombre clave
        # =========================
        nombre = str(hoja).strip().upper()

        # =========================
        # Limpiar columnas
        # =========================
        df.columns = df.columns.map(str).str.strip()

        # =========================
        # Guardar
        # =========================
        hojas[nombre] = df

    return hojas
