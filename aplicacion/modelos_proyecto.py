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

    # 🔹 Fuente de precios materiales
    df_precios_materiales: Optional[pd.DataFrame] = None

    # 🔹 Override manual (OPCIONAL)
    df_costos_estructuras: Optional[pd.DataFrame] = None

    # 🔹 Parámetros operativos (NUEVO)
    costo_cuadrilla_dia: float = 1250
    fraccion_jornada: float = 1/16
    costo_equipos: float = 0.0
    costo_logistica: float = 0.0
    margen_utilidad: float = 0.15

    # 🔹 Control
    calcular_costos: bool = True

    # =====================================================
    # 🔧 VALIDACIÓN
    # =====================================================
    def validar_costos(self):

        if not self.calcular_costos:
            return

        # -----------------------------
        # PRECIOS MATERIALES
        # -----------------------------
        if self.df_precios_materiales is None and not self.ruta_materiales:
            raise ValueError(
                "Debe proporcionar df_precios_materiales o ruta_materiales"
            )

        # -----------------------------
        # PARÁMETROS OPERATIVOS
        # -----------------------------
        if self.costo_cuadrilla_dia <= 0:
            raise ValueError("costo_cuadrilla_dia inválido")

        if self.fraccion_jornada <= 0:
            raise ValueError("fraccion_jornada inválida")

        if self.margen_utilidad < 0:
            raise ValueError("margen_utilidad inválido")
