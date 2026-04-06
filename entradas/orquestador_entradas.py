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
from entradas.base_datos import cargar_base_datos, obtener_ruta_base

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
    Pipeline oficial:

        1. Lectura (raw)
        2. Normalización (parseo real)
        3. Validación estructural
        4. Validación catálogo
        5. Base de datos
        6. DTO limpio
    """

    # =========================
    # 1. LECTURA
    # =========================
    df_raw = _leer_por_tipo(tipo, data)

    if df_raw is None or df_raw.empty:
        raise ValueError("No se pudo leer información válida")

    if "Punto" not in df_raw.columns:
        raise ValueError("Falta columna 'Punto'")

    # =========================
    # 2. NORMALIZACIÓN
    # =========================
    df_norm, errores_norm, warnings_norm = normalizar_estructuras(df_raw)

    if errores_norm:
        raise ValueError("\n".join(errores_norm))

    if df_norm is None or df_norm.empty:
        raise ValueError("Normalización vacía")

    # =========================
    # 3. VALIDACIÓN ESTRUCTURAL 🔥 (NUEVO)
    # =========================
    _validar_dataframe_estructuras(df_norm)

    # =========================
    # 4. VALIDACIÓN CATÁLOGO
    # =========================
    if validar_catalogo:
        ruta = obtener_ruta_base()
        df_indice = cargar_indice_normalizado(ruta)

        df_val, errores_val, warnings_val = validar_estructuras(df_norm, df_indice)

        if errores_val:
            raise ValueError("\n".join(errores_val))

        df_final = df_val
    else:
        df_final = df_norm

    # =========================
    # 5. BASE DE DATOS
    # =========================
    hojas_base = cargar_base_datos()

    # =========================
    # 6. DTO
    # =========================
    return EntradaMateriales(
        estructuras_df=df_final,
        tension=float(tension),
        df_cables=df_cables,
        hojas_base=hojas_base,
        datos_proyecto={
            "materiales_extra": df_materiales_extra
        }
    )


# =========================================================
# VALIDACIÓN ESTRUCTURAL FUERTE 🔥
# =========================================================
def _validar_dataframe_estructuras(df: pd.DataFrame):

    if "codigodeestructura" not in df.columns:
        raise ValueError("Normalización inválida: falta codigodeestructura")

    # 🔥 REGLA CRÍTICA: no debe haber espacios
    invalidos = df["codigodeestructura"].astype(str).str.contains(" ")

    if invalidos.any():
        ejemplos = df.loc[invalidos, "codigodeestructura"].unique()[:5]

        raise ValueError(
            "Estructuras mal parseadas (texto no atómico):\n"
            + "\n".join(ejemplos)
        )


# =========================================================
# LECTORES
# =========================================================
def _leer_por_tipo(tipo: str, data) -> pd.DataFrame:

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


def _leer_desde_ui(data) -> pd.DataFrame:

    if isinstance(data, pd.DataFrame):
        return data.copy()

    if isinstance(data, list):
        return pd.DataFrame(data)

    if isinstance(data, dict):
        return pd.DataFrame([data])

    return pd.DataFrame()
