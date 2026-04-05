# -*- coding: utf-8 -*-

from __future__ import annotations

import pandas as pd
from pathlib import Path


# ==========================================================
# CONFIG
# ==========================================================
def obtener_ruta_base() -> Path:
    """
    Permite cambiar fácilmente la ubicación del archivo en el futuro.
    """
    return Path(__file__).resolve().parent.parent / "data" / "Estructura_datos.xlsx"


# ==========================================================
# CARGA BASE DE DATOS
# ==========================================================
def cargar_base_datos() -> dict[str, pd.DataFrame]:
    """
    Carga todas las hojas del Excel en memoria.

    Retorna:
        dict[str, DataFrame]
    """

    ruta = obtener_ruta_base()

    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {ruta}")

    try:
        xls = pd.ExcelFile(ruta)
    except Exception as e:
        raise RuntimeError(f"Error al abrir el archivo Excel: {e}")

    hojas: dict[str, pd.DataFrame] = {}

    for hoja in xls.sheet_names:
        try:
            # =========================
            # Leer hoja
            # =========================
            df = xls.parse(hoja)

            if df is None or df.empty:
                continue

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

        except Exception as e:
            print(f"[WARN] Error leyendo hoja '{hoja}': {e}")
            continue

    if not hojas:
        raise ValueError("No se pudo cargar ninguna hoja válida del archivo.")

    return hojas
