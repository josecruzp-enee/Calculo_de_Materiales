# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import pandas as pd


@dataclass
class EntradaProyecto:
    """
    Contrato maestro del sistema (Aplicación)
    """

    base_datos: Dict[str, pd.DataFrame]
    df_estructuras: pd.DataFrame

    tension: Optional[float] = None
    datos_proyecto: Dict[str, Any] = field(default_factory=dict)

    calibre_mt: str = ""
    tabla_conectores_mt: Dict[str, Any] = field(default_factory=dict)

    df_cables: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_materiales_extra: pd.DataFrame = field(default_factory=pd.DataFrame)

    df_precios_materiales: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_costos_estructuras: pd.DataFrame = field(default_factory=pd.DataFrame)

    def validar(self) -> bool:

        # BASE DATOS
        if not isinstance(self.base_datos, dict) or not self.base_datos:
            raise ValueError("base_datos inválido o vacío")

        for k, v in self.base_datos.items():
            if not isinstance(v, pd.DataFrame):
                raise TypeError(f"base_datos[{k}] no es DataFrame")

        # ESTRUCTURAS
        if not isinstance(self.df_estructuras, pd.DataFrame):
            raise TypeError("df_estructuras debe ser DataFrame")

        if self.df_estructuras.empty:
            raise ValueError("df_estructuras vacío")

        df = self.df_estructuras.copy()
        df.columns = df.columns.str.strip().str.capitalize()

        columnas_requeridas = {"Estructura", "Cantidad"}
        if not columnas_requeridas.issubset(df.columns):
            raise ValueError(
                f"df_estructuras debe contener columnas {columnas_requeridas}"
            )

        df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce")

        if df["Cantidad"].isna().any():
            raise ValueError("Cantidad contiene valores inválidos")

        if (df["Cantidad"] <= 0).any():
            raise ValueError("Cantidad debe ser mayor a 0")

        self.df_estructuras = df

        # TENSIÓN
        if self.tension is not None:
            try:
                self.tension = float(self.tension)
            except Exception:
                raise ValueError(f"Tensión inválida: {self.tension}")

            if self.tension <= 0:
                raise ValueError("Tensión debe ser mayor a 0")

        # CONECTORES
        if not isinstance(self.tabla_conectores_mt, dict):
            raise TypeError("tabla_conectores_mt debe ser dict")

        # DATAFRAMES OPCIONALES
        for nombre, df_ in {
            "df_cables": self.df_cables,
            "df_materiales_extra": self.df_materiales_extra,
            "df_precios_materiales": self.df_precios_materiales,
            "df_costos_estructuras": self.df_costos_estructuras,
        }.items():
            if df_ is not None and not isinstance(df_, pd.DataFrame):
                raise TypeError(f"{nombre} debe ser DataFrame")

        # NORMALIZACIÓN FINAL
        self.calibre_mt = str(self.calibre_mt or "").strip().upper()

        return True
