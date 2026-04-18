# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional, Dict, Any
import pandas as pd
import traceback

from interfaz.contratos import SalidaInterfaz, SalidaEntradas

# =========================================================
# HELPERS
# =========================================================
def _fail(msg: str) -> SalidaEntradas:
    return SalidaEntradas(
        ok=False,
        errores=[msg],
        warnings=[],
        df_estructuras=None,
        base_datos=None,
        datos_proyecto=None,
        df_cables=None,
    )


def _normalizar_df(df: Optional[pd.DataFrame]) -> pd.DataFrame:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame()

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _validar_estructuras(df: pd.DataFrame) -> pd.DataFrame:

    if df is None or df.empty:
        raise ValueError("df_estructuras vacío")

    df = _normalizar_df(df)

    columnas = set(df.columns)

    if {"Estructura", "Cantidad"}.issubset(columnas):
        pass
    elif {"codigodeestructura", "Cantidad"}.issubset(columnas):
        df = df.rename(columns={"codigodeestructura": "Estructura"})
    else:
        raise ValueError(f"df_estructuras inválido: {list(columnas)}")

    df["Estructura"] = (
        df["Estructura"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["Cantidad"] = pd.to_numeric(
        df["Cantidad"],
        errors="coerce"
    ).fillna(0)

    return df


def _procesar_cables(df_cables: Optional[pd.DataFrame]) -> pd.DataFrame:

    if df_cables is None or not isinstance(df_cables, pd.DataFrame) or df_cables.empty:
        return pd.DataFrame()

    df = df_cables.copy()

    df.columns = [str(c).strip().lower() for c in df.columns]

    if "tipo" in df.columns:
        df["tipo"] = (
            df["tipo"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

    if "longitud" in df.columns:
        df["longitud"] = pd.to_numeric(
            df["longitud"],
            errors="coerce"
        ).fillna(0)

    return df


# =========================================================
# ORQUESTADOR DE ENTRADAS
# =========================================================
def ejecutar_entradas(salida_interfaz: SalidaInterfaz) -> SalidaEntradas:

    try:
        if not salida_interfaz:
            return _fail("SalidaInterfaz es None")

        datos_proyecto = salida_interfaz.datos_proyecto or {}
        base_datos = salida_interfaz.base_datos or {}

        # =====================================================
        # ESTRUCTURAS
        # =====================================================
        df_estructuras = _validar_estructuras(
            salida_interfaz.df_estructuras
        )

        # =====================================================
        # CABLES
        # =====================================================
        df_cables = _procesar_cables(
            salida_interfaz.df_cables
        )

        # =====================================================
        # SALIDA FINAL
        # =====================================================
        return SalidaEntradas(
            ok=True,
            df_estructuras=df_estructuras,
            base_datos=base_datos,
            datos_proyecto=datos_proyecto,
            df_cables=df_cables,
            errores=[],
            warnings=[],
        )

    except Exception as e:
        return SalidaEntradas(
            ok=False,
            errores=[str(e)],
            warnings=[],
            df_estructuras=None,
            base_datos=None,
            datos_proyecto=None,
            df_cables=None,
        )
