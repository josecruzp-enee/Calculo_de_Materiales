from dataclasses import dataclass
from typing import Optional, Dict, Any
import pandas as pd


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
    # 🔥 COSTOS
    # =====================================================
    # Fuente 1: DataFrame directo (prioridad alta)
    df_precios_materiales: Optional[pd.DataFrame] = None

    # Fuente 2: Excel (fallback)
    # 👉 ya es ruta_materiales

    # Costos estructuras (OBLIGATORIO si calcular_costos=True)
    df_costos_estructuras: Optional[pd.DataFrame] = None

    # Control de ejecución
    calcular_costos: bool = True

    # =====================================================
    # 🔧 VALIDACIÓN INTERNA (NUEVO)
    # =====================================================
    def validar_costos(self):
        if not self.calcular_costos:
            return

        if self.df_precios_materiales is None and not self.ruta_materiales:
            raise ValueError(
                "Debe proporcionar df_precios_materiales o ruta_materiales"
            )

        if self.df_costos_estructuras is None:
            raise ValueError(
                "df_costos_estructuras es requerido para cálculo de costos"
            )
