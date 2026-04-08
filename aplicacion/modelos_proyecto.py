from dataclasses import dataclass
from typing import Optional, Dict, Any
import pandas as pd


@dataclass
class EntradaProyecto:
    # =====================================================
    # 🔹 DATOS PRINCIPALES
    # =====================================================
    df_estructuras: pd.DataFrame

    # =====================================================
    # 🔹 OPCIONALES DE ENTRADA
    # =====================================================
    df_cables: Optional[pd.DataFrame] = None
    df_materiales_extra: Optional[pd.DataFrame] = None

    # =====================================================
    # 🔹 CONFIGURACIÓN PROYECTO
    # =====================================================
    ruta_materiales: Optional[str] = None
    tension: Optional[float] = None
    datos_proyecto: Optional[Dict[str, Any]] = None

    # =====================================================
    # 🔥 COSTOS (NUEVO BLOQUE)
    # =====================================================
    # precios de materiales (puede ser DF o Excel)
    df_precios_materiales: Optional[pd.DataFrame] = None

    # costos unitarios de estructuras
    df_costos_estructuras: Optional[pd.DataFrame] = None

    # flag opcional para activar/desactivar costos
    calcular_costos: bool = True
