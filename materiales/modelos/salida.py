# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
import pandas as pd
from typing import List, Optional, Dict, Any


COLUMNAS_STD = ["Materiales", "Unidad", "Cantidad"]


@dataclass(slots=True)
class SalidaMateriales:

    # ======================================================
    # CONTROL
    # ======================================================
    ok: bool = True  # ✔ FIX: default seguro

    errores: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # ======================================================
    # RESULTADOS MATERIALES
    # ======================================================
    df_materiales: Optional[pd.DataFrame] = None
    df_materiales_por_punto: Optional[pd.DataFrame] = None

    # ======================================================
    # RESULTADOS ESTRUCTURAS
    # ======================================================
    df_estructuras: Optional[pd.DataFrame] = None
    df_estructuras_por_punto: Optional[pd.DataFrame] = None
    descripcion_estructuras: Optional[Dict[str, str]] = None
    df_materiales_por_estructura: Optional[Dict[str, pd.DataFrame]] = None

    # ======================================================
    # CONTEXTO
    # ======================================================
    datos_proyecto: Optional[Dict[str, Any]] = None

    # ======================================================
    # DEBUG
    # ======================================================
    debug: Optional[Dict[str, Any]] = None

    # ======================================================
    # VALIDACIÓN
    # ======================================================
    def __post_init__(self):

        # --------------------------
        # CASO ERROR
        # --------------------------
        if not self.ok:
            if not self.errores:
                raise ValueError("ok=False sin errores")
            return

        # --------------------------
        # VALIDAR MATERIALES
        # --------------------------
        if self.df_materiales is None:
            raise ValueError("df_materiales es None con ok=True")

        if not isinstance(self.df_materiales, pd.DataFrame):
            raise TypeError("df_materiales debe ser DataFrame")

        if self.df_materiales.empty:
            raise ValueError("df_materiales vacío")

        if not set(COLUMNAS_STD).issubset(self.df_materiales.columns):
            raise ValueError("df_materiales columnas inválidas")

        if self.df_materiales["Materiales"].isna().any():
            raise ValueError("Materiales contiene nulos")

        if self.df_materiales["Unidad"].isna().any():
            raise ValueError("Unidad contiene nulos")

        cantidades = pd.to_numeric(self.df_materiales["Cantidad"], errors="coerce")

        if cantidades.isna().any():
            raise ValueError("Cantidad inválida")

        if (cantidades < 0).any():
            raise ValueError("Cantidad negativa")

        # --------------------------
        # VALIDAR ESTRUCTURAS
        # --------------------------
        if self.df_estructuras is not None:
            if not isinstance(self.df_estructuras, pd.DataFrame):
                raise TypeError("df_estructuras debe ser DataFrame")

            if not {"Estructura", "Cantidad"}.issubset(self.df_estructuras.columns):
                raise ValueError("df_estructuras formato inválido")

        if self.df_estructuras_por_punto is not None:
            if not isinstance(self.df_estructuras_por_punto, pd.DataFrame):
                raise TypeError("df_estructuras_por_punto debe ser DataFrame")

            if not {"Punto", "Estructura", "Cantidad"}.issubset(
                self.df_estructuras_por_punto.columns
            ):
                raise ValueError("df_estructuras_por_punto formato inválido")

        if self.descripcion_estructuras is not None:
            if not isinstance(self.descripcion_estructuras, dict):
                raise TypeError("descripcion_estructuras debe ser dict")

        # --------------------------
        # CONSISTENCIA FINAL
        # --------------------------
        if self.errores:
            raise ValueError("ok=True pero hay errores")

    # ======================================================
    # HELPERS
    # ======================================================
    def tiene_warnings(self) -> bool:
        return len(self.warnings) > 0

    def cantidad_total(self) -> float:
        return float(self.df_materiales["Cantidad"].sum())
