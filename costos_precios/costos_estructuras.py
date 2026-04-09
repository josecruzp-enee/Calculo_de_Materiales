# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from typing import Dict

# =====================================================
# COSTOS BASE
# =====================================================
from costos_precios.costos_materiales import calcular_costos_desde_resumen


# =====================================================
# 🔹 HELPER: PRECIO UNITARIO DE UNA ESTRUCTURA
# =====================================================
def calcular_precio_unitario_estructura(
    df_materiales: pd.DataFrame,
    df_precios_materiales: pd.DataFrame,
    porcentaje_operativo: float = 0.25,
    margen_utilidad: float = 0.15,
) -> Dict[str, float]:

    # =====================================================
    # VALIDACIONES
    # =====================================================
    if not isinstance(df_materiales, pd.DataFrame) or df_materiales.empty:
        raise ValueError("df_materiales inválido o vacío")

    if not isinstance(df_precios_materiales, pd.DataFrame) or df_precios_materiales.empty:
        raise ValueError("df_precios_materiales inválido o vacío")

    columnas_req = {"Materiales", "Unidad", "Cantidad"}
    if not columnas_req.issubset(set(df_materiales.columns)):
        raise ValueError(f"df_materiales debe contener columnas {columnas_req}")

    # =====================================================
    # LIMPIEZA BÁSICA
    # =====================================================
    df_mat = df_materiales.copy()

    df_mat["Materiales"] = df_mat["Materiales"].astype(str).str.strip()
    df_mat["Unidad"] = df_mat["Unidad"].astype(str).str.strip()
    df_mat["Cantidad"] = pd.to_numeric(df_mat["Cantidad"], errors="coerce").fillna(0)

    if df_mat["Cantidad"].sum() <= 0:
        raise ValueError("Cantidad total de materiales es 0")

    # =====================================================
    # VALORIZACIÓN
    # =====================================================
    df_val = calcular_costos_desde_resumen(
        df_mat[["Materiales", "Unidad", "Cantidad"]],
        df_precios_materiales
    )

    if not isinstance(df_val, pd.DataFrame) or df_val.empty:
        raise ValueError("Error en valorización de materiales")

    if "Tiene_Precio" not in df_val.columns:
        raise ValueError("df_val no contiene columna 'Tiene_Precio'")

    if "Costo" not in df_val.columns:
        raise ValueError("df_val no contiene columna 'Costo'")

    # =====================================================
    # VALIDACIÓN CRÍTICA
    # =====================================================
    if not df_val["Tiene_Precio"].all():
        faltantes = df_val.loc[
            ~df_val["Tiene_Precio"], "Materiales"
        ].unique()

        raise ValueError(
            f"Materiales sin precio: {list(faltantes)}"
        )

    # =====================================================
    # COSTOS
    # =====================================================
    costo_material = float(
        pd.to_numeric(df_val["Costo"], errors="coerce")
        .fillna(0)
        .sum()
    )

    if costo_material <= 0:
        raise ValueError("Costo material inválido (0 o negativo)")

    costo_operativo = costo_material * porcentaje_operativo
    costo_total = costo_material + costo_operativo

    # =====================================================
    # PRECIO
    # =====================================================
    precio_unitario = costo_total * (1 + margen_utilidad)

    if precio_unitario <= 0:
        raise ValueError("Precio unitario inválido")

    return {
        "Costo Material": round(costo_material, 2),
        "Costo Operativo": round(costo_operativo, 2),
        "Costo Unitario": round(costo_total, 2),
        "Precio Unitario": round(precio_unitario, 2),
    }


# =====================================================
# 🔹 FUNCIÓN PRINCIPAL (POR ESTRUCTURA)
# =====================================================
def calcular_costos_por_estructura(
    *,
    df_estructuras: pd.DataFrame,
    df_materiales_por_estructura: Dict[str, pd.DataFrame],
    df_precios_materiales: pd.DataFrame,
    porcentaje_operativo: float = 0.25,
    margen_utilidad: float = 0.15,
) -> pd.DataFrame:

    # =====================================================
    # VALIDACIONES
    # =====================================================
    if not isinstance(df_estructuras, pd.DataFrame) or df_estructuras.empty:
        raise ValueError("df_estructuras inválido o vacío")

    if not isinstance(df_materiales_por_estructura, dict) or not df_materiales_por_estructura:
        raise ValueError("df_materiales_por_estructura inválido")

    if not isinstance(df_precios_materiales, pd.DataFrame) or df_precios_materiales.empty:
        raise ValueError("df_precios_materiales inválido")

    if "Estructura" not in df_estructuras.columns or "Cantidad" not in df_estructuras.columns:
        raise ValueError("df_estructuras debe contener 'Estructura' y 'Cantidad'")

    # =====================================================
    # NORMALIZACIÓN
    # =====================================================
    df = df_estructuras.copy()

    df["Estructura"] = df["Estructura"].astype(str).str.strip().str.upper()
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)

    conteo = dict(zip(df["Estructura"], df["Cantidad"]))

    filas = []

    # =====================================================
    # LOOP PRINCIPAL
    # =====================================================
    for cod, qty in conteo.items():

        qty = int(qty or 0)

        if qty <= 0:
            continue

        df_mat = df_materiales_por_estructura.get(cod)

        if not isinstance(df_mat, pd.DataFrame) or df_mat.empty:
            raise ValueError(f"No hay materiales para estructura: {cod}")

        # -----------------------------------------
        # CÁLCULO
        # -----------------------------------------
        precios = calcular_precio_unitario_estructura(
            df_materiales=df_mat,
            df_precios_materiales=df_precios_materiales,
            porcentaje_operativo=porcentaje_operativo,
            margen_utilidad=margen_utilidad,
        )

        filas.append({
            "codigodeestructura": cod,
            "Cantidad": qty,
            **precios,
            "Total": round(precios["Precio Unitario"] * qty, 2),
        })

    # =====================================================
    # OUTPUT
    # =====================================================
    df_out = pd.DataFrame(filas)

    if df_out.empty:
        raise ValueError("No se generaron costos (resultado vacío)")

    return df_out
