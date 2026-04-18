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
        # 2. ESTRUCTURAS (YA LO TENÍAS)
        # =====================================================
        df_estructuras = salida_interfaz.df_estructuras

        if df_estructuras is None or df_estructuras.empty:
            raise ValueError("df_estructuras vacío")

        # =====================================================
        # 🔥 3. EXTRAER CABLES DEL PROYECTO (NUEVO)
        # =====================================================
        cables_raw = datos_proyecto.get("cables_proyecto", [])

        if cables_raw and isinstance(cables_raw, list):
            try:
                df_cables = pd.DataFrame(cables_raw)

                # Normalización básica (CLAVE)
                df_cables.columns = [c.strip().lower() for c in df_cables.columns]

                if "tipo" in df_cables.columns:
                    df_cables["tipo"] = df_cables["tipo"].astype(str).str.strip().str.upper()

                if "longitud" in df_cables.columns:
                    df_cables["longitud"] = pd.to_numeric(
                        df_cables["longitud"],
                        errors="coerce"
                    ).fillna(0)

            except Exception:
                df_cables = pd.DataFrame()
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
            df_cables=df_cables,   # 🔥 ESTA ES LA CLAVE
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
