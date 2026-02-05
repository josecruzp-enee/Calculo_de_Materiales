# modulo/desplegables.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import pandas as pd

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
RUTA_EXCEL = os.path.join(REPO_ROOT, "data", "Estructura_datos.xlsx")
from modulo.desplegables import RUTA_EXCEL, cargar_opciones
import os, pandas as pd, streamlit as st

with st.expander("🧪 Debug catálogo", expanded=False):
    st.write("Ruta:", RUTA_EXCEL)
    st.write("Existe:", os.path.exists(RUTA_EXCEL))
    if os.path.exists(RUTA_EXCEL):
        xls = pd.ExcelFile(RUTA_EXCEL)
        st.write("Hojas:", xls.sheet_names)

def cargar_opciones(ruta_excel: str | None = None) -> dict:
    ruta = ruta_excel or RUTA_EXCEL

    xls = pd.ExcelFile(ruta)

    hoja = next(
        (s for s in xls.sheet_names if s.strip().lower() in ("indice", "índice")),
        None
    )
    if not hoja:
        raise ValueError("No existe hoja 'indice' / 'Índice'")

    df = pd.read_excel(xls, sheet_name=hoja)
    df.columns = df.columns.astype(str).str.replace("\xa0", " ").str.strip()

    clas_col = "Clasificación" if "Clasificación" in df.columns else "Clasificacion"
    cod_col  = "Código de Estructura" if "Código de Estructura" in df.columns else "Codigo de Estructura"
    desc_col = "Descripción" if "Descripción" in df.columns else "Descripcion"

    for c in (clas_col, cod_col, desc_col):
        if c in df.columns:
            df[c] = df[c].astype(str).str.replace("\xa0", " ").str.strip()

    opciones = {}
    for clas in df[clas_col].dropna().unique():
        sub = df[df[clas_col] == clas]
        codigos = sub[cod_col].dropna().astype(str).tolist()
        etiquetas = {
            c: f"{c} – {sub[sub[cod_col] == c][desc_col].iloc[0]}"
            for c in codigos
        }
        opciones[str(clas)] = {"valores": codigos, "etiquetas": etiquetas}

    mapping = {
        "Poste": "Poste",
        "Primaria": "Primario",
        "Secundaria": "Secundario",
        "Retenidas": "Retenidas",
        "Conexiones a tierra": "Conexiones a tierra",
        "Protección": "Protección",
        "Proteccion": "Protección",
        "Transformadores": "Transformadores",
        "Luminarias": "Luminarias",
        "Luminaria": "Luminarias",
    }

    return {mapping.get(k, k): v for k, v in opciones.items()}

