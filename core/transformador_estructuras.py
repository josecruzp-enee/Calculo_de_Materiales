# core/transformador_estructuras.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

def coerce_df_estructuras_largo(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte/normaliza la tabla de estructuras a formato 'largo' (long).

    NOTA: Esto es un stub mínimo para desbloquear la app.
    Aquí luego metemos la lógica real de transformación.
    """
    if df is None:
        return pd.DataFrame()

    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]

    # Si viene vacío, regresamos igual
    if out.empty:
        return out

    return out
