# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import re
from typing import Dict, Any, Tuple

from ayuda.debug import debug_guardar


# =========================================================
# DEBUG
# =========================================================
def _debug(etapa: str, info: Dict[str, Any]):
    """Debug centralizado para esta función"""
    debug_guardar("MANO_OBRA", etapa, info)


# =========================================================
# FACTORES
# =========================================================
def obtener_fases_desde_codigo(codigo: str) -> int:
    cod = str(codigo).upper()
    match = re.search(r"-([IVX]+)-", cod)
    if not match:
        return 1
    return {"I": 1, "II": 2, "III": 3}.get(match.group(1), 1)


def obtener_factor_fases(fases: int) -> float:
    return {1: 1.0, 2: 1.5, 3: 2.0}.get(fases, 1.0)


def obtener_factor_tipo(codigo: str) -> float:
    cod = str(codigo).strip().upper()

    if cod.startswith("CT"):
        return 1.10
    if cod.startswith("LL"):
        return 0.75
    if cod.startswith("CA"):
        return 0.80
    if cod.startswith(("TS", "T")):
        return 1.80

    return {
        "P": 1.50,
        "A": 1.25,
        "B": 1.00,
        "C": 1.20,
        "R": 1.30,
    }.get(cod[0], 1.0)


def obtener_factor_geometrico(codigo: str) -> float:
    cod = str(codigo).strip().upper()
    match = re.search(r"-(\d+)$", cod)
    if not match:
        return 1.0

    return {
        1: 1.00,
        2: 1.15,
        4: 1.30,
        5: 1.40,
        6: 1.60,
    }.get(int(match.group(1)), 1.0)


def obtener_factor_escala(cantidad: int) -> float:
    if cantidad <= 4:
        return 1.00
    elif cantidad <= 9:
        return 0.93
    elif cantidad <= 19:
        return 0.88
    return 0.82


# =========================================================
# PREPARACIÓN DATOS
# =========================================================
def _validar_entrada(df: pd.DataFrame):
    if df is None or df.empty:
        raise ValueError("df_estructuras vacío")

    if "CODIGO" not in df.columns or "Cantidad" not in df.columns:
        raise ValueError("df_estructuras inválido")


def _normalizar_entrada(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["CODIGO"] = df["CODIGO"].astype(str).str.strip().str.upper()
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)
    return df


def _agrupar_por_codigo(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby("CODIGO", as_index=False)["Cantidad"].sum()


# =========================================================
# LECTURA ÍNDICE
# =========================================================
def _leer_indice(archivo_materiales: str) -> Tuple[Dict, Dict]:
    df_indice = pd.read_excel(archivo_materiales, sheet_name="indice")
    df_indice.columns = [str(c).strip().upper() for c in df_indice.columns]

    # 🔥 YA NO EXISTE "Código de Estructura"
    if "CODIGO" not in df_indice.columns:
        raise ValueError("Falta columna CODIGO")

    if "PRECIO" not in df_indice.columns:
        raise ValueError("Falta columna PRECIO")

    if "DESCRIPCION" not in df_indice.columns:
        df_indice["DESCRIPCION"] = ""

    # 🔥 NORMALIZACIÓN ÚNICA
    df_indice["CODIGO"] = (
        df_indice["CODIGO"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    precio_map = dict(zip(
        df_indice["CODIGO"],
        pd.to_numeric(df_indice["PRECIO"], errors="coerce").fillna(0.0)
    ))

    desc_map = dict(zip(
        df_indice["CODIGO"],
        df_indice["DESCRIPCION"].astype(str)
    ))

    return precio_map, desc_map
# =========================================================
# CÁLCULO POR FILA
# =========================================================
def _calcular_fila(cod: str, qty: int, precio_map, desc_map):

    if cod not in precio_map:
        return None, f"{cod}: sin MO base"

    mo_base = float(precio_map[cod])

    fases = obtener_fases_desde_codigo(cod)
    f_fases = obtener_factor_fases(fases)
    f_tipo = obtener_factor_tipo(cod)
    f_geom = obtener_factor_geometrico(cod)
    f_escala = obtener_factor_escala(qty)

    mo_unit = mo_base * f_fases * f_tipo * f_geom
    mo_total = mo_unit * qty * f_escala

    fila = {
        "CODIGO": cod,
        "Descripcion": desc_map.get(cod, ""),
        "Cantidad": qty,
        "MO Base": round(mo_base, 2),
        "Fases": fases,
        "Factor Fases": f_fases,
        "Factor Tipo": f_tipo,
        "Factor Geometrico": f_geom,
        "Factor Escala": f_escala,
        "MO Unitario Ajustado": round(mo_unit, 2),
        "MO Total": round(mo_total, 2),
    }

    return fila, None


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================
def calcular_mano_obra(
    *,
    df_estructuras: pd.DataFrame,
    archivo_materiales: str,
) -> pd.DataFrame:
    """
    SALIDA:
    -------
    DataFrame con columnas:
        CODIGO, Descripcion, Cantidad,
        MO Base, Fases, Factor Fases,
        Factor Tipo, Factor Geometrico,
        Factor Escala, MO Unitario Ajustado, MO Total
    """

    _validar_entrada(df_estructuras)

    df = _normalizar_entrada(df_estructuras)
    df_group = _agrupar_por_codigo(df)

    precio_map, desc_map = _leer_indice(archivo_materiales)

    filas = []
    errores = []

    for _, row in df_group.iterrows():

        cod = row["CODIGO"]
        qty = int(row["Cantidad"])

        if qty <= 0:
            continue

        fila, err = _calcular_fila(cod, qty, precio_map, desc_map)

        if err:
            errores.append(err)
            continue

        filas.append(fila)

    df_out = pd.DataFrame(filas)

    if df_out.empty:
        _debug("ERROR", {"errores": errores})
        raise ValueError("No se generó mano de obra")

    _debug("RESULTADO", {
        "filas": len(df_out),
        "total_mo": float(df_out["MO Total"].sum()),
        "errores": errores,
    })

    return df_out
