# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any
import pandas as pd

# =========================
# LECTORES
# =========================
from entradas.leer_excel import leer_estructuras
from entradas.leer_tabla import leer_tabla
from entradas.leer_pdf import leer_pdf
from entradas.leer_dxf import leer_dxf

# =========================
# PROCESAMIENTO
# =========================
from entradas.normalizar import normalizar_estructuras
from entradas.validacion import validar_estructuras
from entradas.indice_estructuras import cargar_indice_normalizado
from entradas.base_datos import cargar_base_datos

# =========================
# MODELO
# =========================
from materiales.modelos.entrada import EntradaMateriales


# =========================================================
# ORQUESTADOR PRINCIPAL
# =========================================================
def cargar_entrada(
    tipo: str,
    data: Any,
    *,
    tension: float,
    df_cables: pd.DataFrame | None = None,
    df_materiales_extra: pd.DataFrame | None = None,
    validar_catalogo: bool = True,
) -> EntradaMateriales:
    """
    Punto único de entrada al dominio de materiales.

    Flujo:
        1. Lectura
        2. Validación mínima
        3. Normalización
        4. Validación contra catálogo
        5. Carga base
        6. Construcción DTO
    """

    # =========================
    # 1. LECTURA
    # =========================
    df = _leer_por_tipo(tipo, data)

    if df is None or df.empty:
        raise ValueError("No se pudo leer información válida")

    if "Punto" not in df.columns:
        raise ValueError("Falta columna 'Punto'")

    # =========================
    # 2. NORMALIZACIÓN
    # =========================
    df = normalizar_estructuras(df)

    if df is None or df.empty:
        raise ValueError("Normalización vacía")

    # =========================
    # 3. VALIDACIÓN CATÁLOGO
    # =========================
    if validar_catalogo:
        df_indice = cargar_indice_normalizado()

        df, errores, _ = validar_estructuras(df, df_indice)

        if errores:
            raise ValueError("\n".join(errores))

    # =========================
    # 4. BASE DE DATOS
    # =========================
    hojas_base = cargar_base_datos()

    # =========================
    # 5. DTO
    # =========================
    return EntradaMateriales(
        estructuras_df=df,
        tension=float(tension),
        df_cables=df_cables,
        hojas_base=hojas_base,
        datos_proyecto={
            "materiales_extra": df_materiales_extra
        }
    )


# =========================================================
# LECTORES POR TIPO
# =========================================================
def _leer_por_tipo(tipo: str, data) -> pd.DataFrame:
    """
    Dispatcher de lectura según tipo de entrada.
    """

    if tipo == "excel":
        return leer_estructuras(data)

    if tipo == "tabla":
        return leer_tabla(data)

    if tipo == "pdf":
        return leer_pdf(data)

    if tipo == "dxf":
        return leer_dxf(data)

    if tipo == "ui":
        return _leer_desde_ui(data)

    raise ValueError(f"Tipo no soportado: {tipo}")


# =========================================================
# LECTOR UI
# =========================================================
def _leer_desde_ui(data) -> pd.DataFrame:
    """
    Convierte datos de UI a DataFrame estándar.
    """

    if isinstance(data, pd.DataFrame):
        return data.copy()

    if isinstance(data, list):
        return pd.DataFrame(data)

    if isinstance(data, dict):
        return pd.DataFrame([data])

    return pd.DataFrame()
