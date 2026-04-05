# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any
import pandas as pd

from entradas.leer_excel import leer_estructuras
from entradas.leer_tabla import leer_tabla
from entradas.leer_pdf import leer_pdf
from entradas.leer_dxf import leer_dxf

from entradas.normalizar import normalizar_estructuras
from entradas.validacion import validar_estructuras
from entradas.indice_estructuras import cargar_indice_normalizado
from entradas.base_datos import cargar_base_datos

from materiales.modelos.entrada import EntradaMateriales


def cargar_entrada(
    tipo: str | None = None,
    data: Any = None,
    *,
    datos_fuente: dict | None = None,
    tension: float | None = None,
    df_cables: pd.DataFrame | None = None,
    ruta_materiales: str | None = None,
    permitir_sin_catalogo: bool = False,
) -> EntradaMateriales:

    log = _get_logger()

    # 🔧 FIX
    df_materiales_extra = None

    # =========================
    # UI
    # =========================
    if datos_fuente is not None:

        df = _leer_desde_ui(datos_fuente.get("df_estructuras"))
        df_cables = datos_fuente.get("df_cables")
        df_materiales_extra = datos_fuente.get("df_materiales_extra")

    else:
        df = _leer_por_tipo(tipo, data)

    # =========================
    # VALIDACIÓN
    # =========================
    if df is None or df.empty:
        raise ValueError("No se pudo leer información válida")

    if "Punto" not in df.columns:
        raise ValueError("Falta columna 'Punto'")

    # =========================
    # NORMALIZACIÓN
    # =========================
    df = normalizar_estructuras(df)

    if df is None or df.empty:
        raise ValueError("Normalización vacía")

    # =========================
    # VALIDACIÓN CATÁLOGO
    # =========================
    if ruta_materiales and not permitir_sin_catalogo:

        df_indice = cargar_indice_normalizado(ruta_materiales, log)

        df, errores, warnings = validar_estructuras(df, df_indice, log)

        if errores:
            raise ValueError("\n".join(errores))

    # =========================
    # TENSIÓN
    # =========================
    if tension is None:
        raise ValueError("tension es requerida")

    # =========================
    # BASE
    # =========================
    hojas_base = None
    if ruta_materiales:
        hojas_base = cargar_base_datos()

    return EntradaMateriales(
        estructuras_df=df,
        tension=float(tension),
        df_cables=df_cables,
        hojas_base=hojas_base,
        datos_proyecto={
            "materiales_extra": df_materiales_extra
        }
    )


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


def _leer_desde_ui(data):

    if isinstance(data, pd.DataFrame):
        return data.copy()

    if isinstance(data, list):
        return pd.DataFrame(data)

    if isinstance(data, dict):
        return pd.DataFrame([data])

    return pd.DataFrame()


def _get_logger():
    def _log(msg):
        print(msg)
    return _log
