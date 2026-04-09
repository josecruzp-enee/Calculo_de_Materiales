# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Union
import pandas as pd
from pathlib import Path

# =====================================================
# COSTOS BASE
# =====================================================
from costos_precios.costos_materiales import calcular_costos_desde_resumen
from costos_precios.costos_por_punto import calcular_costos_por_punto


# =====================================================
# CONTRATO FUERTE
# =====================================================
@dataclass
class EntradaCostos:
    df_resumen: pd.DataFrame
    df_estructuras_por_punto: pd.DataFrame
    df_costos_estructuras: pd.DataFrame
    fuente_precios: Union[pd.DataFrame, str, Path]


# =====================================================
# HELPERS
# =====================================================
def _cols_norm(df: pd.DataFrame) -> set:
    return {str(c).strip().lower() for c in df.columns}


def _validar_df(nombre: str, df: pd.DataFrame, cols_minimas=None):
    if df is None or not isinstance(df, pd.DataFrame):
        raise TypeError(f"{nombre} debe ser DataFrame")

    if df.empty:
        raise ValueError(f"{nombre} está vacío")

    if cols_minimas:
        cols = _cols_norm(df)
        faltantes = [c for c in cols_minimas if c not in cols]
        if faltantes:
            raise ValueError(
                f"{nombre} no tiene columnas requeridas: {faltantes}. "
                f"Columnas actuales: {list(df.columns)}"
            )


def _validar_fuente_precios(fuente: Union[pd.DataFrame, str, Path]):
    if fuente is None:
        raise ValueError("fuente_precios es requerido")

    # DataFrame
    if isinstance(fuente, pd.DataFrame):
        if fuente.empty:
            raise ValueError("df_precios_materiales está vacío")
        return fuente

    # Ruta
    if isinstance(fuente, (str, Path)):
        ruta = Path(fuente)
        if not ruta.exists():
            raise FileNotFoundError(f"Archivo de precios no existe: {ruta}")
        return ruta

    raise TypeError("fuente_precios debe ser DataFrame o ruta válida")


# =====================================================
# ORQUESTADOR COSTOS (PRO)
# =====================================================
def ejecutar_costos(entrada: EntradaCostos) -> Dict[str, Any]:

    debug = {}

    # =====================================================
    # VALIDACIÓN DE CONTRATO
    # =====================================================
    if not isinstance(entrada, EntradaCostos):
        raise TypeError("entrada debe ser EntradaCostos")

    debug["input"] = {
        "df_resumen_rows": len(entrada.df_resumen) if isinstance(entrada.df_resumen, pd.DataFrame) else 0,
        "df_resumen_cols": list(entrada.df_resumen.columns) if isinstance(entrada.df_resumen, pd.DataFrame) else [],

        "df_estructuras_rows": len(entrada.df_estructuras_por_punto) if isinstance(entrada.df_estructuras_por_punto, pd.DataFrame) else 0,
        "df_estructuras_cols": list(entrada.df_estructuras_por_punto.columns) if isinstance(entrada.df_estructuras_por_punto, pd.DataFrame) else [],

        "df_costos_estructuras_rows": len(entrada.df_costos_estructuras) if isinstance(entrada.df_costos_estructuras, pd.DataFrame) else 0,
        "df_costos_estructuras_cols": list(entrada.df_costos_estructuras.columns) if isinstance(entrada.df_costos_estructuras, pd.DataFrame) else [],

        "fuente_precios_tipo": str(type(entrada.fuente_precios))
    }

    # =====================================================
    # VALIDACIONES
    # =====================================================
    _validar_df(
        "df_resumen",
        entrada.df_resumen,
        cols_minimas=["materiales", "cantidad"]
    )

    _validar_df("df_estructuras_por_punto", entrada.df_estructuras_por_punto)
    cols_ep = _cols_norm(entrada.df_estructuras_por_punto)

    debug["check_estructuras_cols"] = list(cols_ep)

    if not ({"estructura", "codigodeestructura", "punto"} & cols_ep):
        raise ValueError("df_estructuras_por_punto inválido")

    _validar_df(
        "df_costos_estructuras",
        entrada.df_costos_estructuras,
        cols_minimas=["estructura"]
    )

    fuente_precios = _validar_fuente_precios(entrada.fuente_precios)

    debug["fuente_precios"] = {
        "tipo": str(type(fuente_precios)),
        "preview": fuente_precios.head(3).to_dict() if isinstance(fuente_precios, pd.DataFrame) else str(fuente_precios)
    }

    # =====================================================
    # 1. COSTOS DE MATERIALES
    # =====================================================
    df_costos_materiales = calcular_costos_desde_resumen(
        entrada.df_resumen,
        fuente_precios
    )

    debug["costos_materiales"] = {
        "rows": len(df_costos_materiales) if isinstance(df_costos_materiales, pd.DataFrame) else 0,
        "cols": list(df_costos_materiales.columns) if isinstance(df_costos_materiales, pd.DataFrame) else [],
        "preview": df_costos_materiales.head(3).to_dict() if isinstance(df_costos_materiales, pd.DataFrame) else {}
    }

    if df_costos_materiales is None or not isinstance(df_costos_materiales, pd.DataFrame):
        raise RuntimeError("calcular_costos_desde_resumen retornó inválido")

    if df_costos_materiales.empty:
        raise ValueError("df_costos_materiales vacío (sin match de precios)")

    # =====================================================
    # 2. COSTOS POR PUNTO
    # =====================================================
    out = calcular_costos_por_punto(
        entrada.df_estructuras_por_punto,
        entrada.df_costos_estructuras
    )

    debug["costos_por_punto_raw"] = {
        "tipo": str(type(out)),
        "len": len(out) if isinstance(out, (list, tuple)) else "no_iterable"
    }

    if not isinstance(out, (tuple, list)) or len(out) != 3:
        raise RuntimeError("calcular_costos_por_punto mal retorno")

    df_detalle, df_resumen_costos, df_resumen_precios = out

    debug["costos_por_punto"] = {
        "detalle_rows": len(df_detalle) if isinstance(df_detalle, pd.DataFrame) else 0,
        "resumen_rows": len(df_resumen_costos) if isinstance(df_resumen_costos, pd.DataFrame) else 0,
        "precios_rows": len(df_resumen_precios) if isinstance(df_resumen_precios, pd.DataFrame) else 0,

        "detalle_cols": list(df_detalle.columns) if isinstance(df_detalle, pd.DataFrame) else [],
        "resumen_cols": list(df_resumen_costos.columns) if isinstance(df_resumen_costos, pd.DataFrame) else [],
        "precios_cols": list(df_resumen_precios.columns) if isinstance(df_resumen_precios, pd.DataFrame) else [],

        "detalle_preview": df_detalle.head(3).to_dict() if isinstance(df_detalle, pd.DataFrame) else {}
    }

    # =====================================================
    # OUTPUT
    # =====================================================
    return {
        "ok": True,
        "debug": debug,

        "df_costos_materiales": df_costos_materiales,
        "df_costos_estructuras": entrada.df_costos_estructuras,
        "df_costos_por_punto": df_detalle,
        "df_resumen_costos_punto": df_resumen_costos,
        "df_resumen_precios_punto": df_resumen_precios,
    }
