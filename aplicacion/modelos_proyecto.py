# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import Optional, Dict, Any
import pandas as pd


@dataclass
class EntradaProyecto:
    """
    Contrato de entrada principal del sistema.
    Totalmente alineado con orquestador_proyecto.
    """

    # =====================================================
    # 🔹 DATA PRINCIPAL
    # =====================================================
    df_estructuras: pd.DataFrame

    # =====================================================
    # 🔹 OPCIONALES (MATERIALES)
    # =====================================================
    df_cables: Optional[pd.DataFrame] = None
    df_materiales_extra: Optional[pd.DataFrame] = None

    # =====================================================
    # 🔹 CONTEXTO
    # =====================================================
    ruta_materiales: Optional[str] = None
    tension: Optional[float] = None
    datos_proyecto: Optional[Dict[str, Any]] = None

    # =====================================================
    # 🔹 COSTOS - INPUTS
    # =====================================================
    df_precios_materiales: Optional[pd.DataFrame] = None
    df_costos_estructuras: Optional[pd.DataFrame] = None

    # =====================================================
    # 🔹 COSTOS - PARÁMETROS
    # =====================================================
    costo_cuadrilla_dia: float = 1250
    fraccion_jornada: float = 1 / 16
    costo_equipos: float = 0.0
    costo_logistica: float = 0.0
    margen_utilidad: float = 0.15

    calcular_costos: bool = True

    # =====================================================
    # 🔹 VALIDACIÓN
    # =====================================================
    def validar(self):

        # -------------------------------
        # ESTRUCTURAS
        # -------------------------------
        if self.df_estructuras is None or self.df_estructuras.empty:
            raise ValueError("df_estructuras vacío")

        # -------------------------------
        # CONTEXTO
        # -------------------------------
        if self.datos_proyecto is None:
            self.datos_proyecto = {}

        # fallback de tensión
        if self.tension is None:
            self.tension = self.datos_proyecto.get("tension")

        # -------------------------------
        # COSTOS
        # -------------------------------
        if not self.calcular_costos:
            return

        # precios
        if self.df_precios_materiales is None and not self.ruta_materiales:
            raise ValueError(
                "Debe proporcionar df_precios_materiales o ruta_materiales"
            )

        # costos por estructura
        if self.df_costos_estructuras is None:
            raise ValueError("Falta df_costos_estructuras")

        # parámetros
        if self.costo_cuadrilla_dia <= 0:
            raise ValueError("costo_cuadrilla_dia inválido")

        if self.fraccion_jornada <= 0:
            raise ValueError("fraccion_jornada inválido")

        if self.margen_utilidad < 0:
            raise ValueError("margen_utilidad inválido")
