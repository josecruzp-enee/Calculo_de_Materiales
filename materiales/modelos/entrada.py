# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import Optional, Dict, Any
import pandas as pd


@dataclass(slots=True)
class EntradaMateriales:
    estructuras_df: pd.DataFrame
    tension: float

    # opcionales (según tu flujo actual)
    df_cables: Optional[pd.DataFrame] = None
    calibre_mt: Optional[str] = None
    tabla_conectores_mt: Optional[Dict[str, Any]] = None
