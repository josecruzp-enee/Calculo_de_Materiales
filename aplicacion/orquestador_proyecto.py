# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Any
import pandas as pd

from interfaz.contratos import SalidaInterfaz
from entradas.modelos import SalidaEntradas


# =========================================================
# ORQUESTADOR DE ENTRADAS
# =========================================================
def ejecutar_entradas(salida_interfaz: SalidaInterfaz) -> SalidaEntradas:

    try:
        # =====================================================
        # 1. VALIDACIÓN BÁSICA
        # =====================================================
        if not salida_interfaz:
            raise ValueError("SalidaInterfaz es None")

        datos_proyecto = salida_interfaz.datos_proyecto or {}
        base_datos = salida_interfaz.base_datos or {}

        # =====================================================
        # 2. ESTRUCTURAS
        # =====================================================
        df_estructuras = salida_interfaz.df_estructuras

        if df_estructuras is None or df_estructuras.empty:
            raise ValueError("df_estructuras vacío")

        # =====================================================
        # 🔥 3. CABLES (CORREGIDO)
        # =====================================================
        df_cables = salida_interfaz.df_cables  # 👈 ESTE ES EL FIX

        if isinstance(df_cables, pd.DataFrame) and not df_cables.empty:

            df_cables = df_cables.copy()

            # normalizar nombres
            df_cables.columns = [c.strip().lower() for c in df_cables.columns]

            # normalizar tipo
            if "tipo" in df_cables.columns:
                df_cables["tipo"] = (
                    df_cables["tipo"]
                    .astype(str)
                    .str.strip()
                    .str.upper()
                )

            # normalizar longitud
            if "longitud" in df_cables.columns:
                df_cables["longitud"] = pd.to_numeric(
                    df_cables["longitud"],
                    errors="coerce"
                ).fillna(0)

        else:
            df_cables = pd.DataFrame()

        # =====================================================
        # 4. SALIDA FINAL
        # =====================================================
        return SalidaEntradas(
            ok=True,
            df_estructuras=df_estructuras,
            base_datos=base_datos,
            datos_proyecto=datos_proyecto,
            df_cables=df_cables,
        )

    except Exception as e:
        return SalidaEntradas(
            ok=False,
            errores=[str(e)],
            warnings=[],
            df_estructuras=None,
            base_datos=None,
            datos_proyecto=None,
            df_cables=None,
        )
