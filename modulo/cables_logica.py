# -*- coding: utf-8 -*-
"""
cables_logica.py
Validación, cálculo y extracción de cables desde materiales.
"""

from __future__ import annotations
import pandas as pd
import re
from typing import Dict, List, Tuple

from .cables_catalogo import get_calibres, get_calibres_union, get_configs_por_tipo, get_configs_union
from .cables_normalizacion import _norm_key, _norm_txt, calibre_corto_desde_seleccion, conductores_de


# =========================
# Catálogo oficial (TU LISTA)
# =========================
CABLES_OFICIALES: Dict[Tuple[str, str], str] = {
    # Retenidas (acerado)
    ("RETENIDA", "1/4"):  'Cable Acerado 1/4"',
    ("RETENIDA", "5/16"): 'Cable Acerado 5/16"',
    ("RETENIDA", "3/8"):  'Cable Acerado 3/8"',

    # BT forrado WP (Quince/Fig/Peach)
    ("BT", "2 WP"):     "Cable de Aluminio Forrado WP # 2 AWG Peach",
    ("BT", "1/0 WP"):   "Cable de Aluminio Forrado WP # 1/0 AWG Quince",
    ("BT", "3/0 WP"):   "Cable de Aluminio Forrado WP # 3/0 AWG Fig",
    ("BT", "266.8 MCM"): "Cable BT 266.8 MCM",  # ajustá si tenías nombre real

    # MT ACSR (ejemplos)
    ("MT", "1/0 ACSR"): "Cable de Aluminio ACSR # 1/0 AWG Raven",
    ("MT", "2 ACSR"):   "Cable de Aluminio ACSR # 2 AWG",
    ("MT", "266.8 MCM"): "Cable de Aluminio ACSR 266.8 MCM",
}


def _persistir_oficial(st) -> None:
    """
    Guarda el catálogo oficial en session_state para usarlo en UI/PDF si querés.
    """
    st.session_state.setdefault("cables_oficiales", {})
    st.session_state["cables_oficiales"] = {f"{k[0]}|{k[1]}": v for k, v in CABLES_OFICIALES.items()}


def descripcion_oficial(tipo: str, calibre: str) -> str:
    k = (_norm_key(tipo), _norm_key(calibre))
    # fallback: probar calibre corto
    if k in CABLES_OFICIALES:
        return CABLES_OFICIALES[k]
    k2 = (_norm_key(tipo), _norm_key(calibre_corto_desde_seleccion(calibre)))
    return CABLES_OFICIALES.get(k2, _norm_txt(f"{tipo} {calibre}"))


def _resumen_por_calibre(df: pd.DataFrame) -> Dict[str, float]:
    """
    Resumen simple: suma Longitud por 'Tipo+Calibre'
    """
    if df is None or df.empty:
        return {}
    tmp = df.copy()
    tmp["Tipo"] = tmp["Tipo"].astype(str)
    tmp["Calibre"] = tmp["Calibre"].astype(str)
    tmp["Longitud"] = pd.to_numeric(tmp["Longitud"], errors="coerce").fillna(0.0)

    out = {}
    for (t, c), grp in tmp.groupby(["Tipo", "Calibre"]):
        key = f"{t} | {c}"
        out[key] = float(grp["Longitud"].sum())
    return out


def _validar_y_calcular(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia y calcula columnas derivadas.
    Espera columnas: Tipo, Calibre, Config, Longitud, Unidad, Conductores, Incluir
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["Tipo", "Calibre", "Config", "Longitud", "Unidad", "Conductores", "Incluir", "Descripcion"])

    out = df.copy()
    out["Tipo"] = out["Tipo"].astype(str).map(_norm_txt)
    out["Calibre"] = out["Calibre"].astype(str).map(_norm_txt)
    out["Config"] = out.get("Config", "").astype(str).map(_norm_txt)
    out["Unidad"] = out.get("Unidad", "m").astype(str).map(_norm_txt)

    out["Longitud"] = pd.to_numeric(out.get("Longitud", 0), errors="coerce").fillna(0.0)
    out["Incluir"] = out.get("Incluir", True).astype(bool)

    # Conductores: si viene vacío lo inferimos por tipo
    if "Conductores" not in out.columns:
        out["Conductores"] = ""
    out["Conductores"] = out["Conductores"].astype(str).map(_norm_txt)
    mask_empty = out["Conductores"].str.strip().eq("")
    out.loc[mask_empty, "Conductores"] = out.loc[mask_empty, "Tipo"].map(conductores_de)

    # Descripción oficial
    out["Descripcion"] = [
        descripcion_oficial(t, c) for t, c in zip(out["Tipo"].tolist(), out["Calibre"].tolist())
    ]

    # filtrar filas sin tipo/calibre o longitud cero (opcional)
    out = out[(out["Tipo"].str.strip() != "") & (out["Calibre"].str.strip() != "")]
    return out.reset_index(drop=True)


def _extraer_cables_desde_materiales(df_materiales: pd.DataFrame) -> pd.DataFrame:
    """
    Extrae cables a partir de df_materiales si tu app guarda materiales en session_state.
    Regla: detectar palabras clave y luego construir tabla base.
    """
    if df_materiales is None or df_materiales.empty:
        return pd.DataFrame()

    df = df_materiales.copy()
    if "Materiales" not in df.columns:
        return pd.DataFrame()

    s = df["Materiales"].astype(str)

    # filtro simple: contiene Cable
    mask = s.str.contains(r"\bCable\b", case=False, na=False)
    dfc = df[mask].copy()
    if dfc.empty:
        return pd.DataFrame()

    # Tabla mínima para editor
    out = pd.DataFrame({
        "Tipo": "",
        "Calibre": "",
        "Config": "",
        "Longitud": 0.0,
        "Unidad": "m",
        "Conductores": "",
        "Incluir": True,
    })

    # Si querés extraer calibre real del texto, aquí lo podés mejorar luego.
    # Por ahora, devolvemos plantilla vacía si detectó cables.
    return out
