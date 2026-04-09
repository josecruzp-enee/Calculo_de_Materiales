# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import pandas as pd


@dataclass
class EntradaProyecto:

    # =====================================================
    # BASE OBLIGATORIA
    # =====================================================
    df_estructuras: pd.DataFrame = field(default_factory=pd.DataFrame)
    ruta_materiales: str = ""

    # =====================================================
    # CONFIGURACIÓN DEL PROYECTO
    # =====================================================
    tension: Optional[float] = None
    datos_proyecto: Dict[str, Any] = field(default_factory=dict)

    # =====================================================
    # INPUTS DE DOMINIO (🔥 CORREGIDO)
    # =====================================================
    calibre_mt: str = ""

    # 🔥 CAMBIO CLAVE: ahora dict (no DataFrame)
    tabla_conectores_mt: Dict[str, Any] = field(default_factory=dict)

    # estos sí siguen siendo tabulares
    df_cables: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_materiales_extra: pd.DataFrame = field(default_factory=pd.DataFrame)

    # =====================================================
    # COSTOS
    # =====================================================
    df_precios_materiales: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_costos_estructuras: pd.DataFrame = field(default_factory=pd.DataFrame)

    # =====================================================
    # VALIDACIÓN FUERTE
    # =====================================================
    def validar(self):

        # 🔹 estructuras
        if not isinstance(self.df_estructuras, pd.DataFrame):
            raise TypeError("df_estructuras debe ser DataFrame")

        if self.df_estructuras.empty:
            raise ValueError("df_estructuras vacío")

        # 🔹 ruta
        if not self.ruta_materiales:
            raise ValueError("ruta_materiales requerida")

        # 🔹 tensión
        if self.tension is not None:
            try:
                self.tension = float(self.tension)
            except Exception:
                raise ValueError(f"Tensión inválida: {self.tension}")

            if self.tension <= 0:
                raise ValueError("Tensión debe ser mayor a 0")

        # 🔹 tabla conectores (🔥 alineado con materiales)
        if not isinstance(self.tabla_conectores_mt, dict):
            raise TypeError("tabla_conectores_mt debe ser dict")

        # 🔹 normalización básica
        self.calibre_mt = str(self.calibre_mt or "").strip().upper()

        return True
