# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import Optional, Dict, Any
import pandas as pd


@dataclass(slots=True)
class EntradaMateriales:
    estructuras_df: pd.DataFrame
    tension: float

    # opcionales
    df_cables: Optional[pd.DataFrame] = None
    calibre_mt: Optional[str] = None
    tabla_conectores_mt: Optional[Dict[str, Any]] = None

    # ======================================================
    # VALIDACIÓN AUTOMÁTICA
    # ======================================================
    def __post_init__(self):

        # --------------------------
        # estructuras_df
        # --------------------------
        if self.estructuras_df is None:
            raise ValueError("estructuras_df es None")

        if not isinstance(self.estructuras_df, pd.DataFrame):
            raise TypeError("estructuras_df debe ser DataFrame")

        if self.estructuras_df.empty:
            raise ValueError("estructuras_df está vacío")

        if "Estructuras" not in self.estructuras_df.columns:
            raise ValueError("estructuras_df debe contener columna 'Estructuras'")

        # --------------------------
        # tensión
        # --------------------------
        try:
            self.tension = float(self.tension)
        except Exception:
            raise ValueError(f"Tensión inválida: {self.tension}")

        if self.tension <= 0:
            raise ValueError("Tensión debe ser mayor que 0")

        # --------------------------
        # df_cables
        # --------------------------
        if self.df_cables is not None:
            if not isinstance(self.df_cables, pd.DataFrame):
                raise TypeError("df_cables debe ser DataFrame")

        # --------------------------
        # calibre
        # --------------------------
        if self.calibre_mt is not None:
            self.calibre_mt = str(self.calibre_mt).strip().upper()

        # --------------------------
        # tabla conectores
        # --------------------------
        if self.tabla_conectores_mt is not None:
            if not isinstance(self.tabla_conectores_mt, dict):
                raise TypeError("tabla_conectores_mt debe ser dict")
