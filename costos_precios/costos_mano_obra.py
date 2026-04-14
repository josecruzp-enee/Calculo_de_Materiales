# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import re
from typing import Dict, Any

from ayuda.debug import debug_guardar


# =========================================================
# FACTOR FASES (DESDE CÓDIGO)
# =========================================================
def obtener_fases_desde_codigo(codigo: str) -> int:

    cod = str(codigo).upper()

    match = re.search(r"-([IVX]+)-", cod)

    if not match:
        return 1

    return {
        "I": 1,
        "II": 2,
        "III": 3,
    }.get(match.group(1), 1)


def obtener_factor_fases(fases: int) -> float:

    return {
        1: 1.0,
        2: 1.5,
        3: 2.0,
    }.get(fases, 1.0)


# =========================================================
# FACTOR TIPO
# =========================================================
def obtener_factor_tipo(codigo: str) -> float:

    cod = str(codigo).strip().upper()

    if cod.startswith("CT"):
        return 1.10
    if cod.startswith("LL"):
        return 0.75
    if cod.startswith("CA"):
        return 0.80
    if cod.startswith("TS") or cod.startswith("T"):
        return 1.80

    tipo = cod[0]

    return {
        "P": 1.50,
        "A": 1.25,
        "B": 1.00,
        "C": 1.20,
        "R": 1.30,
    }.get(tipo, 1.0)


# =========================================================
# FACTOR GEOMÉTRICO (DESDE CÓDIGO)
# =========================================================
def obtener_factor_geometrico(codigo: str) -> float:

    cod = str(codigo).strip().upper()

    match = re.search(r"-(\d+)$", cod)

    if not match:
        return 1.0

    tipo = int(match.group(1))

    return {
        1: 1.00,  # Paso
        2: 1.15,  # Ángulo
        4: 1.30,  # Remate
        5: 1.40,  # Doble remate
        6: 1.60,  # Giro
    }.get(tipo, 1.0)


# =========================================================
# FACTOR ESCALA
# =========================================================
def obtener_factor_escala(cantidad: int) -> float:

    if cantidad <= 4:
        return 1.00
    elif cantidad <= 9:
        return 0.93
    elif cantidad <= 19:
        return 0.88
    else:
        return 0.82


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================
def calcular_mano_obra(
    *,
    df_estructuras: pd.DataFrame,
    archivo_materiales: str,
) -> pd.DataFrame:

    debug: Dict[str, Any] = {}

    # =====================================================
    # VALIDACIONES
    # =====================================================
    if df_estructuras is None or df_estructuras.empty:
        raise ValueError("df_estructuras vacío")

    # =====================================================
    # NORMALIZAR
    # =====================================================
    df = df_estructuras.copy()

    if "Estructura" not in df.columns or "Cantidad" not in df.columns:
        raise ValueError("df_estructuras inválido")

    df["codigodeestructura"] = df["Estructura"].astype(str).str.strip().str.upper()
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)

    # =====================================================
    # AGRUPAR (MISMO CRITERIO QUE COSTOS)
    # =====================================================
    df_group = df.groupby("codigodeestructura", as_index=False)["Cantidad"].sum()

    # =====================================================
    # LEER ÍNDICE (MO BASE)
    # =====================================================
    df_indice = pd.read_excel(archivo_materiales, sheet_name="indice")
    df_indice.columns = [str(c).strip() for c in df_indice.columns]

    if "Código de Estructura" not in df_indice.columns:
        raise ValueError("Falta 'Código de Estructura'")

    if "Precio" not in df_indice.columns:
        raise ValueError("Falta 'Precio'")

    if "Descripción" not in df_indice.columns:
        df_indice["Descripción"] = ""

    df_indice["cod_norm"] = df_indice["Código de Estructura"].astype(str).str.strip().str.upper()

    precio_map = dict(
        zip(
            df_indice["cod_norm"],
            pd.to_numeric(df_indice["Precio"], errors="coerce").fillna(0.0)
        )
    )

    desc_map = dict(
        zip(
            df_indice["cod_norm"],
            df_indice["Descripción"].astype(str)
        )
    )

    # =====================================================
    # PROCESO
    # =====================================================
    filas = []
    errores = []

    for _, row in df_group.iterrows():

        cod = str(row["codigodeestructura"])
        qty = int(row["Cantidad"])

        if qty <= 0:
            continue

        if cod not in precio_map:
            errores.append(f"{cod}: sin MO base")
            continue

        mo_base = float(precio_map[cod])

        # 🔥 FACTORES AUTOMÁTICOS
        fases = obtener_fases_desde_codigo(cod)
        f_fases = obtener_factor_fases(fases)
        f_tipo = obtener_factor_tipo(cod)
        f_geom = obtener_factor_geometrico(cod)
        f_escala = obtener_factor_escala(qty)

        # 🔥 MODELO
        mo_unit = mo_base * f_fases * f_tipo * f_geom
        mo_total = mo_unit * qty * f_escala

        filas.append({
            "codigodeestructura": cod,
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
        })

    df_out = pd.DataFrame(filas)

    if df_out.empty:
        debug_guardar("MO_ERROR", {
            "errores": errores,
            "estructuras": df_group.head(20).to_dict(),
        })
        raise ValueError("No se generó mano de obra")

    debug_guardar("MANO_OBRA", {
        "filas": len(df_out),
        "total_mo": float(df_out["MO Total"].sum()),
        "errores": errores,
    })

    return df_out
