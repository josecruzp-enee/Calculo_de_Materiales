# -*- coding: utf-8 -*-
"""
entradas_dxf.py

Entrada desde DXF (ENEE).
Devuelve el paquete estándar:
    datos_proyecto, df_estructuras, df_cables, df_materiales_extra
"""

from __future__ import annotations

from typing import Dict, Any, Tuple
import pandas as pd

# Aquí puedes pegar debajo TODA tu lógica DXF (regex + leer_dxf_bytes + extraer_estructuras_desde_dxf + explotar_codigos_largos)
# o copiarla desde tu interfaz.
# Por ahora, este wrapper asume que tendrás estas funciones disponibles:
#   - leer_dxf_bytes(data: bytes) -> doc
#   - extraer_estructuras_desde_dxf(doc, capa_objetivo="") -> df_ancho
#   - (opcional) expand_wide_to_long(df_ancho) -> df_largo
#   - explotar_codigos_largos(df_largo) -> df_largo


def _df_vacio(cols):
    return pd.DataFrame(columns=list(cols))


def cargar_desde_dxf(datos_fuente: Dict[str, Any]) -> Tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    datos_fuente espera:
      - archivo_dxf: bytes (recomendado) o ruta (str)
      - capa: str opcional
      - datos_proyecto: dict opcional
    """
    datos_proyecto = dict(datos_fuente.get("datos_proyecto") or {})
    capa = str(datos_fuente.get("capa") or "").strip()

    # cables y materiales extra: por DXF normalmente vacíos
    df_cables = _df_vacio(["Tipo", "Configuración", "Calibre", "Longitud (m)"])
    df_materiales_extra = _df_vacio(["Materiales", "Unidad", "Cantidad"])

    # --- obtener bytes DXF ---
    data = datos_fuente.get("archivo_dxf")
    ruta = datos_fuente.get("ruta_dxf")

    if data is None and ruta is None:
        raise ValueError("DXF: falta 'archivo_dxf' (bytes) o 'ruta_dxf' (str) en datos_fuente.")

    if data is None and ruta is not None:
        with open(str(ruta), "rb") as f:
            data = f.read()

    # --- leer DXF ---
    doc = leer_dxf_bytes(data)  # noqa: F821

    # --- extraer df ancho ---
    df_ancho = extraer_estructuras_desde_dxf(doc, capa_objetivo=capa if capa else "")  # noqa: F821

    # Si tu motor consume LARGO, aquí conviertes. Si consume ANCHO, retornas df_ancho.
    # Yo te recomiendo devolver df_estructuras como LARGO (lo que ya consumes en tu motor).
    df_largo = expand_wide_to_long(df_ancho)  # noqa: F821
    df_largo = explotar_codigos_largos(df_largo)  # noqa: F821

    df_estructuras = df_largo

    return datos_proyecto, df_estructuras, df_cables, df_materiales_extra
