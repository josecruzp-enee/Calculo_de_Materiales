# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import Optional, Dict, Any
import pandas as pd


@dataclass(slots=True)
class EntradaMateriales:
    estructuras_df: pd.DataFrame
    tension: float
    base_datos: Dict[str, pd.DataFrame] 

    # 👇 NUEVO (CLAVE)
    datos_proyecto: Optional[Dict[str, Any]] = None

    # opcionales
    df_cables: Optional[pd.DataFrame] = None
    df_materiales_extra: Optional[pd.DataFrame] = None
    calibre_mt: Optional[str] = None
    tabla_conectores_mt: Optional[Dict[str, Any]] = None

    # ======================================================
    # VALIDACIÓN AUTOMÁTICA
    # ======================================================
    def __post_init__(self):

        # --------------------------
        # estructuras_df
        # --------------------------
        if not isinstance(self.estructuras_df, pd.DataFrame):
            raise TypeError("estructuras_df debe ser DataFrame")

        if self.estructuras_df.empty:
            raise ValueError("estructuras_df está vacío")

        cols = {c.strip().upper(): c for c in self.estructuras_df.columns}
        col_est = cols.get("ESTRUCTURAS") or cols.get("ESTRUCTURA")

        if not col_est:
            raise ValueError(f"No existe columna de estructuras. Columnas: {list(self.estructuras_df.columns)}")

        self.estructuras_df = self.estructuras_df.rename(columns={col_est: "Estructura"})

        if "Estructura" not in self.estructuras_df.columns:
            raise ValueError("estructuras_df debe contener columna 'Estructura'")

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
        # datos_proyecto 👇
        # --------------------------
        if self.datos_proyecto is not None:
            if not isinstance(self.datos_proyecto, dict):
                raise TypeError("datos_proyecto debe ser dict")

            # opcional: normalizar claves
            self.datos_proyecto = {
                str(k).strip().lower(): v
                for k, v in self.datos_proyecto.items()
            }

        # --------------------------
        # df_cables
        # --------------------------
        if self.df_cables is not None:
            if not isinstance(self.df_cables, pd.DataFrame):
                raise TypeError("df_cables debe ser DataFrame")

        # --------------------------
        # df_materiales_extra
        # --------------------------
        if self.df_materiales_extra is not None:
            if not isinstance(self.df_materiales_extra, pd.DataFrame):
                raise TypeError("df_materiales_extra debe ser DataFrame")

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
