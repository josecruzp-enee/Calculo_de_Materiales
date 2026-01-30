# -*- coding: utf-8 -*-
"""
entradas_pegar_tabla.py
Entrada mediante texto pegado.
"""

from __future__ import annotations
from typing import Dict, Any, Tuple
import pandas as pd


def cargar_desde_pegar_tabla(datos_fuente: Dict[str, Any]) -> Tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    datos_proyecto = dict(datos_fuente.get("datos_proyecto") or {})
    df_estructuras = pd.DataFrame()
    df_cables = pd.DataFrame()
    df_materiales_extra = pd.DataFrame()
    return datos_proyecto, df_estructuras, df_cables, df_materiales_extra
