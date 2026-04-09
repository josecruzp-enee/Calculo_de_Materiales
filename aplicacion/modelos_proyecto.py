from dataclasses import dataclass
from typing import Optional, Dict, Any
import pandas as pd


@dataclass
class EntradaProyecto:

    # =========================
    # BASE
    # =========================
    df_estructuras: pd.DataFrame

    # =========================
    # CONFIG PROYECTO
    # =========================
    ruta_materiales: Optional[str] = None
    tension: Optional[float] = None
    datos_proyecto: Optional[Dict[str, Any]] = None

    # =========================
    # 🔥 NECESARIOS (ANTES TE FALTABAN)
    # =========================
    calibre_mt: Optional[str] = None
    tabla_conectores_mt: Optional[pd.DataFrame] = None

    # =========================
    # COSTOS
    # =========================
    df_precios_materiales: Optional[pd.DataFrame] = None
    df_costos_estructuras: Optional[pd.DataFrame] = None

    # =========================
    # VALIDACIÓN FUERTE
    # =========================
    def validar(self):

        if self.df_estructuras is None or self.df_estructuras.empty:
            raise ValueError("df_estructuras vacío")

        if not self.ruta_materiales:
            raise ValueError("ruta_materiales requerida")

        return True
