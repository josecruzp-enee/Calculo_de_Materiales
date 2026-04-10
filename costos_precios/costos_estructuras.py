# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from typing import Dict, Any

from costos_precios.costos_materiales import calcular_lista_materiales_con_costos
from ayuda.debug import debug_guardar
from entradas.normalizar import limpiar_codigo  # 🔥 CLAVE


# =========================================================
# COSTO UNITARIO DE UNA ESTRUCTURA
# =========================================================
def _costo_unitario_estructura(
    df_materiales: pd.DataFrame,
    df_precios: pd.DataFrame
) -> float:

    import streamlit as st

    # ============================
    # DEBUG ENTRADA
    # ============================
    st.write("🧩 DEBUG → _costo_unitario_estructura")

    st.write("Materiales (head):", df_materiales.head(10))
    st.write("Precios (head):", df_precios.head(10))

    st.write("Cols materiales:", list(df_materiales.columns))
    st.write("Cols precios:", list(df_precios.columns))

    if "Descripcion" in df_materiales.columns and "Descripcion" in df_precios.columns:
        st.write("MATERIALES DESC:", df_materiales["Descripcion"].drop_duplicates().head(10))
        st.write("CATALOGO DESC:", df_precios["Descripcion"].drop_duplicates().head(10))

    # ============================
    # CÁLCULO
    # ============================
    df_val = calcular_lista_materiales_con_costos(
        df_materiales=df_materiales,
        df_catalogo_costos=df_precios
    )

    # ============================
    # DEBUG RESULTADO
    # ============================
    st.write("Resultado df_val:", df_val)

    if df_val is not None:
        st.write("df_val columnas:", list(df_val.columns))
        st.write("df_val head:", df_val.head(10))
        st.write("filas df_val:", len(df_val))

    # ============================
    # VALIDACIONES DURAS
    # ============================
    if df_val is None:
        raise ValueError("df_val es None")

    if df_val.empty:
        raise ValueError("df_val vacío → NO HUBO MATCH DE COSTOS")

    if "Costo Total" not in df_val.columns:
        raise ValueError(f"Columnas inválidas en df_val: {list(df_val.columns)}")

    total = df_val["Costo Total"].sum()

    if pd.isna(total) or total == 0:
        raise ValueError("Costo total = 0 → fallo en precios o match")

    return float(total)
# =========================================================
# COSTOS POR ESTRUCTURA
# =========================================================
def calcular_costos_por_estructura(
    *,
    df_estructuras: pd.DataFrame,
    df_materiales_por_estructura: Dict[str, pd.DataFrame],
    df_precios_materiales: pd.DataFrame,
) -> pd.DataFrame:

    debug: Dict[str, Any] = {}

    # =====================================================
    # VALIDACIONES
    # =====================================================
    if df_estructuras is None or df_estructuras.empty:
        raise ValueError("df_estructuras vacío")

    if df_precios_materiales is None or df_precios_materiales.empty:
        raise ValueError("df_precios_materiales vacío")

    if not isinstance(df_materiales_por_estructura, dict):
        raise TypeError("df_materiales_por_estructura debe ser dict")

    # =====================================================
    # NORMALIZAR CLAVES 🔥 (UNIFICADO)
    # =====================================================
    df_materiales_por_estructura = {
        limpiar_codigo(str(k)): v
        for k, v in df_materiales_por_estructura.items()
    }

    debug["materiales_keys_sample"] = list(df_materiales_por_estructura.keys())[:20]

    # =====================================================
    # NORMALIZAR DATAFRAME DE ESTRUCTURAS 🔥
    # =====================================================
    df = df_estructuras.copy()

    if "Estructura" not in df.columns or "Cantidad" not in df.columns:
        raise ValueError("df_estructuras debe tener columnas 'Estructura' y 'Cantidad'")

    df["codigodeestructura"] = df["Estructura"].map(limpiar_codigo)
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)

    # AGRUPAR
    df_group = df.groupby("codigodeestructura", as_index=False)["Cantidad"].sum()

    debug["estructuras_detectadas"] = len(df_group)
    debug["estructuras_sample"] = df_group.head(10).to_dict()

    filas = []
    errores = []

    # =====================================================
    # LOOP PRINCIPAL
    # =====================================================
    for _, row in df_group.iterrows():

        cod = row["codigodeestructura"]
        qty = float(row["Cantidad"])

        debug[f"estructura::{cod}"] = {
            "cantidad": qty
        }

        if qty <= 0:
            continue

        df_mat = df_materiales_por_estructura.get(cod)

        if df_mat is None or df_mat.empty:
            errores.append(f"Sin materiales para {cod}")
            continue

        try:
            costo_unit = _costo_unitario_estructura(df_mat, df_precios_materiales)

            filas.append({
                "codigodeestructura": cod,
                "Costo Unitario": round(costo_unit, 2),
                "Cantidad": qty,
                "Costo Total": round(costo_unit * qty, 2),
            })

        except Exception as e:
            errores.append(f"{cod}: {str(e)}")

    # =========================================================
    # OUTPUT
    # =========================================================
    df_out = pd.DataFrame(filas)

    if df_out.empty:
        debug_guardar("COSTOS_ESTRUCTURA_ERROR", {
            "errores": errores,
            "materiales_keys": list(df_materiales_por_estructura.keys())[:20],
            "estructuras": df_group.head(20).to_dict(),
            "warning": "No se generaron costos"
        })
        raise ValueError("No se generaron costos por estructura")

    debug["resultado"] = {
        "filas": len(df_out),
        "total_costos": float(df_out["Costo Total"].sum())
    }

    debug["errores"] = errores

    debug_guardar("COSTOS_POR_ESTRUCTURA", debug)

    return df_out
