# -*- coding: utf-8 -*-
"""
entradas.py

Orquestador de entradas.
Devuelve SIEMPRE el mismo paquete estándar.
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
    modo:
        'excel' | 'pegar_tabla' | 'desplegables' | 'pdf' | 'dxf'

    datos_fuente:
        dict con lo necesario según el modo
    """
    modo = str(modo).strip().lower()

    # -----------------------------
    # Valores por defecto (siempre)
    # -----------------------------
    datos_proyecto = {}
    df_cables = _df_vacio(["Tipo", "Configuración", "Calibre", "Longitud (m)"])
    df_materiales_extra = _df_vacio(["Materiales", "Unidad", "Cantidad"])

    # =============================
    # EXCEL → SOLO ESTRUCTURAS
    # =============================
    if modo == "excel":
        from .entradas_excel import (
            leer_datos_proyecto_desde_excel,
            leer_estructuras_desde_excel,
        )

        ruta = datos_fuente["archivo_excel"]

        datos_proyecto = leer_datos_proyecto_desde_excel(ruta)
        df_estructuras = leer_estructuras_desde_excel(ruta)

    # =============================
    # PEGAR TABLA
    # =============================
    elif modo == "pegar_tabla":
        from .entradas_pegar_tabla import cargar_desde_pegar_tabla
        df_estructuras = cargar_desde_pegar_tabla(datos_fuente)

    # =============================
    # LISTAS DESPLEGABLES
    # =============================
    elif modo == "desplegables":
        from .entradas_desplegables import cargar_desde_desplegables
        df_estructuras = cargar_desde_desplegables(datos_fuente)

    # =============================
    # PDF ENEE
    # =============================
    elif modo == "pdf":
        from .entradas_pdf import cargar_desde_pdf
        df_estructuras = cargar_desde_pdf(datos_fuente)

    # =============================
    # DXF ENEE
    # =============================
    elif modo == "dxf":
        from .entradas_dxf import cargar_desde_dxf
        df_estructuras = cargar_desde_dxf(datos_fuente)

    else:
        raise ValueError(f"Modo de entrada no soportado: {modo}")

    # =============================
    # PAQUETE ESTÁNDAR (ÚNICO)
    # =============================
    return {
        "datos_proyecto": datos_proyecto,
        "df_estructuras": df_estructuras,
        "df_cables": df_cables,
        "df_materiales_extra": df_materiales_extra,
    }
