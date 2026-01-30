# -*- coding: utf-8 -*-
"""
entradas_desplegables.py

Entrada mediante listas desplegables (selecciones en UI).
"""

from __future__ import annotations

from typing import Dict, Any, Tuple
import pandas as pd


def cargar_desde_desplegables(datos_fuente: Dict[str, Any]) -> Tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Espera en datos_fuente:
        - "datos_proyecto": dict (opcional)
        - "df_estructuras": DataFrame (si ya lo construye la UI)
        - "df_cables": DataFrame (si ya lo construye la UI)
        - "df_materiales_extra": DataFrame (opcional)

    Retorna:
        datos_proyecto, df_estructuras, df_cables, df_materiales_extra
    """
    datos_proyecto = dict(datos_fuente.get("datos_proyecto") or {})

    df_estructuras = datos_fuente.get("df_estructuras")
    df_cables = datos_fuente.get("df_cables")
    df_materiales_extra = datos_fuente.get("df_materiales_extra")

    if df_estructuras is None:
        df_estructuras = pd.DataFrame()
    if df_cables is None:
        df_cables = pd.DataFrame()
    if df_materiales_extra is None:
        df_materiales_extra = pd.DataFrame()

    return datos_proyecto, df_estructuras, df_cables, df_materiales_extra
