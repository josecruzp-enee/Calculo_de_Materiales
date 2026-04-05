# -*- coding: utf-8 -*-
"""
cables_logica.py
Validación, cálculo y extracción de cables desde materiales.

Decisión de negocio:
- La longitud SIEMPRE está en metros.
- Conductores se calcula automáticamente por Tipo+Config.
- No usamos columnas 'Unidad' ni 'Incluir' en la tabla.
"""

from __future__ import annotations

import pandas as pd
from typing import Dict, Tuple

from core.cables_normalizacion import _norm_key, _norm_txt, calibre_corto_desde_seleccion, conductores_de



# =========================
# Catálogo oficial (TU LISTA)
# =========================
CABLES_OFICIALES: Dict[Tuple[str, str], str] = {
    # Retenidas (acerado)
    ("RETENIDA", "1/4"):  'Cable Acerado 1/4"',
    ("RETENIDA", "5/16"): 'Cable Acerado 5/16"',
    ("RETENIDA", "3/8"):  'Cable Acerado 3/8"',

    # BT forrado WP (Quince/Fig/Peach)
    ("BT", "2 WP"):       "Cable de Aluminio Forrado WP # 2 AWG Peach",
    ("BT", "1/0 WP"):     "Cable de Aluminio Forrado WP # 1/0 AWG Quince",
    ("BT", "3/0 WP"):     "Cable de Aluminio Forrado WP # 3/0 AWG Fig",
    ("BT", "266.8 MCM"):  "Cable de Aluminio Forrado 266.8 MCM Mulberry",

    # MT ACSR (ejemplos)
    ("MT", "1/0 ACSR"):   "Cable de Aluminio ACSR # 1/0 AWG Raven",
    ("MT", "2 ACSR"):     "Cable de Aluminio ACSR # 2 AWG",
    ("MT", "266.8 MCM"):  "Cable de Aluminio ACSR 266.8 MCM",
}


def _persistir_oficial(st) -> None:
    """
    (Opcional) Guarda el catálogo oficial en session_state.
    No es obligatorio para el cálculo, solo por si querés usarlo en UI/PDF.
    """
    st.session_state.setdefault("cables_oficiales", {})
    st.session_state["cables_oficiales"] = {f"{k[0]}|{k[1]}": v for k, v in CABLES_OFICIALES.items()}


def descripcion_oficial(tipo: str, calibre_o_desc: str) -> str:
    """
    Devuelve la descripción oficial.
    Si el usuario pegó una descripción del catálogo, la respeta;
    si pegó calibre corto, intenta mapear.
    """
    t = _norm_key(tipo)
    c_txt = _norm_txt(calibre_o_desc)

    # 1) match directo por (TIPO, CALIBRE)
    k = (t, _norm_key(c_txt))
    if k in CABLES_OFICIALES:
        return CABLES_OFICIALES[k]

    # 2) intentar convertir selección -> calibre corto (firma: (tipo, texto))
    cal_corto = calibre_corto_desde_seleccion(tipo, calibre_o_desc)
    k2 = (t, _norm_key(cal_corto))
    if k2 in CABLES_OFICIALES:
        return CABLES_OFICIALES[k2]

    # 3) fallback
    return _norm_txt(f"{tipo} {calibre_o_desc}")


def _resumen_por_calibre(df: pd.DataFrame) -> Dict[str, float]:
    """
    Resumen simple: suma Longitud (m) por 'Tipo | Calibre'
    """
    if df is None or df.empty:
        return {}

    tmp = df.copy()

    # Asegurar columnas
    if "Tipo" not in tmp.columns:
        tmp["Tipo"] = ""
    if "Calibre" not in tmp.columns:
        tmp["Calibre"] = ""
    if "Longitud" not in tmp.columns:
        tmp["Longitud"] = 0.0

    tmp["Tipo"] = tmp["Tipo"].astype(str).map(_norm_txt)
    tmp["Calibre"] = tmp["Calibre"].astype(str).map(_norm_txt)
    tmp["Longitud"] = pd.to_numeric(tmp["Longitud"], errors="coerce").fillna(0.0)

    out: Dict[str, float] = {}
    for (t, c), grp in tmp.groupby(["Tipo", "Calibre"]):
        key = f"{t} | {c}"
        out[key] = float(grp["Longitud"].sum())
    return out


def _validar_y_calcular(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia y calcula columnas derivadas.

    Entrada mínima esperada:
      - Tipo
      - Calibre
      - Config
      - Longitud   (metros)

    Salida:
      - Tipo, Calibre, Config, Longitud
      - Conductores (calculado)
      - Total Cable (m) (calculado)
      - Descripcion (oficial/fallback)
    """
    cols_out = ["Tipo", "Calibre", "Config", "Longitud", "Conductores", "Total Cable (m)", "Descripcion"]

    if df is None or df.empty:
        return pd.DataFrame(columns=cols_out)

    out = df.copy()

    # Asegurar columnas (evita .get(...,"") que puede devolver string sin .astype)
    if "Tipo" not in out.columns:
        out["Tipo"] = ""
    if "Calibre" not in out.columns:
        out["Calibre"] = ""
    if "Config" not in out.columns:
        out["Config"] = ""
    if "Longitud" not in out.columns:
        out["Longitud"] = 0.0

    # Normalización
    out["Tipo"] = out["Tipo"].astype(str).map(_norm_txt)
    out["Calibre"] = out["Calibre"].astype(str).map(_norm_txt)
    out["Config"] = out["Config"].astype(str).map(_norm_txt)
    out["Longitud"] = pd.to_numeric(out["Longitud"], errors="coerce").fillna(0.0)

    # Filtrar filas sin datos mínimos
    out = out[(out["Tipo"].str.strip() != "") & (out["Calibre"].str.strip() != "")].copy()

    # Conductores automático: depende de Tipo + Config
    out["Conductores"] = [
        int(conductores_de(t, cfg)) for t, cfg in zip(out["Tipo"].tolist(), out["Config"].tolist())
    ]

    # Total en metros
    out["Total Cable (m)"] = out["Longitud"].astype(float) * out["Conductores"].astype(float)

    # Descripción oficial
    out["Descripcion"] = [
        descripcion_oficial(t, c) for t, c in zip(out["Tipo"].tolist(), out["Calibre"].tolist())
    ]

    out = out.reindex(columns=cols_out)
    return out.reset_index(drop=True)


def _extraer_cables_desde_materiales(df_materiales: pd.DataFrame) -> pd.DataFrame:
    """
    (Opcional) Detecta si hay cables en la tabla de materiales y devuelve una plantilla base
    para el editor de cables.

    NOTA: Ya no devolvemos Unidad/Incluir.
    """
    if df_materiales is None or df_materiales.empty:
        return pd.DataFrame()

    if "Materiales" not in df_materiales.columns:
        return pd.DataFrame()

    s = df_materiales["Materiales"].astype(str)
    mask = s.str.contains(r"\b(CABLE|ALAMBRE|CONDUCTOR)\b", case=False, na=False)
    if not mask.any():
        return pd.DataFrame()

    # Plantilla mínima para el editor
    return pd.DataFrame(columns=["Tipo", "Calibre", "Config", "Longitud"])
