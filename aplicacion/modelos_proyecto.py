# -*- coding: utf-8 -*-
# aplicacion/modelos_proyecto.py

from __future__ import annotations
from dataclasses import dataclass
import pandas as pd


@dataclass
class EntradaProyecto:
    """
    DTO limpio entre UI y dominio.
    NO depende de Streamlit.
    """
    df_estructuras: pd.DataFrame
    df_cables: pd.DataFrame | None = None
    df_materiales_extra: pd.DataFrame | None = None
    ruta_materiales: str | None = None
