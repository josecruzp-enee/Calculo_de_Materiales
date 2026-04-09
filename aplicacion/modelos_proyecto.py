# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import pandas as pd


@dataclass
class EntradaProyecto:
    """
    Contrato maestro del sistema (Aplicación)

    RESPONSABILIDAD:
    - Validar inputs
    - Garantizar estructura mínima
    - NO transformar lógica de negocio
    - NO ejecutar cálculos
    """

    # =========================
    # BASE OBLIGATORIA
    # =========================
    base_datos: Dict[str, pd.DataFrame]
    df_estructuras: pd.DataFrame

    # =========================
    # CONFIG PROYECTO
    # =========================
    tension: Optional[float] = None
    datos_proyecto: Dict[str, Any] = field(default_factory=dict)

    # =========================
    # DOMINIO ELÉCTRICO
    # =========================
    calibre_mt: str = ""
    tabla_conectores_mt: Dict[str, str] = field(default_factory=dict)

    # =========================
    # OPCIONALES
    # =========================
    df_cables: Optional[pd.DataFrame] = None
    df_materiales_extra: Optional[pd.DataFrame] = None

    df_precios_materiales: Optional[pd.DataFrame] = None
    df_costos_estructuras: Optional[pd.DataFrame] = None

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    def validar(self) -> None:
        """
        Valida integridad del contrato.

        ❌ NO transforma lógica de negocio
        ❌ NO ejecuta cálculos
        ✔ Solo valida estructura y tipos
        """

        # =====================================================
        # BASE DATOS
        # =====================================================
        if not isinstance(self.base_datos, dict) or not self.base_datos:
            raise ValueError("base_datos inválido o vacío")

        for k, v in self.base_datos.items():
            if not isinstance(v, pd.DataFrame):
                raise TypeError(f"base_datos[{k}] no es DataFrame")

        # =====================================================
        # ESTRUCTURAS
        # =====================================================
        if not isinstance(self.df_estructuras, pd.DataFrame):
            raise TypeError("df_estructuras debe ser DataFrame")

        if self.df_estructuras.empty:
            raise ValueError("df_estructuras vacío")

        columnas = set(c.strip().capitalize() for c in self.df_estructuras.columns)

        columnas_requeridas = {"Estructura", "Cantidad"}
        if not columnas_requeridas.issubset(columnas):
            raise ValueError(
                f"df_estructuras debe contener columnas {columnas_requeridas}"
            )

        # Validación sin mutar
        df_tmp = self.df_estructuras.copy()
        df_tmp.columns = df_tmp.columns.str.strip().str.capitalize()

        df_tmp["Cantidad"] = pd.to_numeric(df_tmp["Cantidad"], errors="coerce")

        if df_tmp["Cantidad"].isna().any():
            raise ValueError("Cantidad contiene valores inválidos")

        if (df_tmp["Cantidad"] <= 0).any():
            raise ValueError("Cantidad debe ser mayor a 0")

        # =====================================================
        # TENSIÓN
        # =====================================================
        if self.tension is not None:
            try:
                t = float(self.tension)
            except Exception:
                raise ValueError(f"Tensión inválida: {self.tension}")

            if t <= 0:
                raise ValueError("Tensión debe ser mayor a 0")

        # =====================================================
        # CONECTORES MT
        # =====================================================
        if not isinstance(self.tabla_conectores_mt, dict):
            raise TypeError("tabla_conectores_mt debe ser dict")

        # Validación ligera de contenido
        for k, v in self.tabla_conectores_mt.items():
            if not isinstance(k, str):
                raise TypeError("Clave de tabla_conectores_mt debe ser str")
            if not isinstance(v, str):
                raise TypeError("Valor de tabla_conectores_mt debe ser str")

        # =====================================================
        # DATAFRAMES OPCIONALES
        # =====================================================
        for nombre, df_ in {
            "df_cables": self.df_cables,
            "df_materiales_extra": self.df_materiales_extra,
            "df_precios_materiales": self.df_precios_materiales,
            "df_costos_estructuras": self.df_costos_estructuras,
        }.items():
            if df_ is not None and not isinstance(df_, pd.DataFrame):
                raise TypeError(f"{nombre} debe ser DataFrame o None")

        # =====================================================
        # NORMALIZACIÓN LIGERA (SEGURA)
        # =====================================================
        self.calibre_mt = str(self.calibre_mt or "").strip().upper()
