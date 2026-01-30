# -*- coding: utf-8 -*-
"""
entradas.py

Orquestador de entradas: selecciona la fuente y devuelve el paquete estándar.
"""

from __future__ import annotations
from typing import Dict, Any
import pandas as pd


def _df_vacio(cols):
    return pd.DataFrame(columns=list(cols))


def cargar_entradas(modo: str, *, datos_fuente: Dict[str, Any]) -> Dict[str, Any]:
    """
    modo: 'excel' | 'pegar_tabla' | 'desplegables' | 'pdf' | 'dxf'
    datos_fuente: diccionario con lo necesario según el modo (rutas, texto, df, etc.)
    """
    modo = str(modo).strip().lower()

    if modo == "excel":
        from .entradas_excel import (
            leer_datos_proyecto_desde_excel,
            leer_estructuras_desde_excel,
            leer_materiales_adicionales_desde_excel,
        )
        ruta = datos_fuente["archivo_excel"]
        datos_proyecto = leer_datos_proyecto_desde_excel(ruta)
        df_estructuras = leer_estructuras_desde_excel(ruta)
        df_materiales_extra = leer_materiales_adicionales_desde_excel(ruta)
        df_cables = _df_vacio(["Tipo", "Configuración", "Calibre", "Longitud (m)"])

    elif modo == "pegar_tabla":
        from .entradas_pegar_tabla import cargar_desde_pegar_tabla
        datos_proyecto, df_estructuras, df_cables, df_materiales_extra = cargar_desde
