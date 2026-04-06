# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
import pandas as pd
from typing import List

COLUMNAS_STD = ["Materiales", "Unidad", "Cantidad"]


@dataclass(slots=True)
class ResultadoMateriales:
    ok: bool
    df_materiales: pd.DataFrame
    errores: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # ======================================================
    # VALIDACIÓN AUTOMÁTICA
    # ======================================================
    def __post_init__(self):

        # --------------------------
        # df_materiales
        # --------------------------
        if self.df_materiales is None:
            raise ValueError("df_materiales es None")

        if not isinstance(self.df_materiales, pd.DataFrame):
            raise TypeError("df_materiales debe ser DataFrame")

        if self.ok:

            if self.df_materiales.empty:
                raise ValueError("df_materiales vacío con ok=True")

            if not set(COLUMNAS_STD).issubset(self.df_materiales.columns):
                raise ValueError("df_materiales no tiene columnas válidas")

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
        # coherencia ok / errores
        # --------------------------
        if self.ok and self.errores:
            raise ValueError("Resultado inconsistente: ok=True pero hay errores")

        if not self.ok and not self.errores:
            raise ValueError("Resultado inconsistente: ok=False sin errores")

    # ======================================================
    # HELPERS ÚTILES
    # ======================================================
    def tiene_warnings(self) -> bool:
        return len(self.warnings) > 0

    def cantidad_total(self) -> float:
        if self.df_materiales.empty:
            return 0.0
        return float(self.df_materiales["Cantidad"].sum())
