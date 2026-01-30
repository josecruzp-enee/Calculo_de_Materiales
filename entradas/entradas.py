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


def cargar_entradas(
    modo: str,
    *,
    datos_fuente: Dict[str, Any],
) -> Dict[str, Any]:
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
        from .entradas_pegar_tabla import cargar_desde_texto
        datos_proyecto, df_estructuras, df_cables, df_materiales_extra = cargar_desde_texto(datos_fuente)

    elif modo == "desplegables":
        from .entradas_desplegables import cargar_desde_desplegables
        datos_proyecto, df_estructuras, df_cables, df_materiales_extra = cargar_desde_desplegables(datos_fuente)

    elif modo == "pdf":
        from .entradas_pdf import cargar_desde_pdf
        datos_proyecto, df_estructuras, df_cables, df_materiales_extra = cargar_desde_pdf(datos_fuente)

    elif modo == "dxf":
        from .entradas_dxf import cargar_desde_dxf
        datos_proyecto, df_estructuras, df_cables, df_materiales_extra = cargar_desde_dxf(datos_fuente)

    else:
        raise ValueError(f"Modo de entrada no soportado: {modo}")

    return {
        "datos_proyecto": datos_proyecto,
        "df_estructuras": df_estructuras,
        "df_cables": df_cables,
        "df_materiales_extra": df_materiales_extra,
    }

