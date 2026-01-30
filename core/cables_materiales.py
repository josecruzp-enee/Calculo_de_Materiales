# core/cables_materiales.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

def materiales_desde_cables(df_cables: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte el DF calculado de cables (UI) a un DF de materiales:
    columnas: Codigo, Descripcion, Unidad, Cantidad, Origen
    """
    cols = ["Codigo", "Descripcion", "Unidad", "Cantidad", "Origen"]
    if df_cables is None or not isinstance(df_cables, pd.DataFrame) or df_cables.empty:
        return pd.DataFrame(columns=cols)

    df = df_cables.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # Preferimos 'Total Cable (m)'. Si no existe, usamos Longitud*Conductores o Longitud
    if "Total Cable (m)" in df.columns:
        qty = pd.to_numeric(df["Total Cable (m)"], errors="coerce").fillna(0.0)
    else:
        L = pd.to_numeric(df.get("Longitud", 0), errors="coerce").fillna(0.0)
        n = pd.to_numeric(df.get("Conductores", 1), errors="coerce").fillna(1.0)
        qty = L * n

    tipo = df.get("Tipo", "").astype(str).str.strip()
    calibre = df.get("Calibre", "").astype(str).str.strip()
    config = df.get("Config", "").astype(str).str.strip()

    out = pd.DataFrame({
        # Codigo: podés hacerlo más “ENE” después con un catálogo.
        "Codigo": ("CABLE-" + tipo + "-" + calibre).str.replace(" ", "", regex=False),
        "Descripcion": ("Cable " + tipo + " " + calibre + " " + config).str.strip(),
        "Unidad": "m",
        "Cantidad": qty,
        "Origen": "Cables",
    })

    out = out[out["Cantidad"] > 0].reset_index(drop=True)
    return out
