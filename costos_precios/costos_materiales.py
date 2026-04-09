# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import unicodedata


# =========================================================
# NORMALIZACIÓN TEXTO
# =========================================================
def _norm_txt(s: object) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""

    t = str(s).strip()

    t = "".join(
        c for c in unicodedata.normalize("NFD", t)
        if unicodedata.category(c) != "Mn"
    )

    return " ".join(t.split()).upper()


# =========================================================
# VALIDADOR PRECIOS (CONTRATO FUERTE)
# =========================================================
def _validar_df_precios(df: pd.DataFrame) -> pd.DataFrame:

    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("df_precios inválido o vacío")

    required = {"Materiales_norm", "Unidad_norm", "Precio Unitario"}

    if not required.issubset(df.columns):
        raise ValueError(
            f"df_precios debe contener columnas {required}"
        )

    df = df.copy()

    # Limpieza fuerte
    df["Materiales_norm"] = df["Materiales_norm"].astype(str).str.strip()
    df["Unidad_norm"] = df["Unidad_norm"].astype(str).str.strip()

    df["Precio Unitario"] = pd.to_numeric(
        df["Precio Unitario"], errors="coerce"
    )

    # Eliminar inválidos
    df = df[df["Precio Unitario"] > 0]

    # Eliminar duplicados (CRÍTICO)
    df = df.drop_duplicates(
        subset=["Materiales_norm", "Unidad_norm"],
        keep="first"
    )

    if df.empty:
        raise ValueError("df_precios sin datos válidos")

    return df


# =========================================================
# COSTO DESDE RESUMEN (CONTRATO LIMPIO)
# =========================================================
def calcular_costos_desde_resumen(
    df_resumen: pd.DataFrame,
    df_precios: pd.DataFrame,
) -> pd.DataFrame:

    # =====================================================
    # VALIDACIÓN INPUT
    # =====================================================
    if not isinstance(df_resumen, pd.DataFrame) or df_resumen.empty:
        raise ValueError("df_resumen inválido o vacío")

    required = {"Materiales", "Cantidad"}
    if not required.issubset(df_resumen.columns):
        raise ValueError(f"df_resumen inválido: requiere {required}")

    df_precios = _validar_df_precios(df_precios)

    # =====================================================
    # LIMPIEZA BASE
    # =====================================================
    base = df_resumen.copy()

    base.columns = [str(c).strip() for c in base.columns]

    if "Unidad" not in base.columns:
        base["Unidad"] = ""

    base["Materiales"] = base["Materiales"].astype(str).str.strip()
    base["Unidad"] = base["Unidad"].astype(str).str.strip()

    base["Cantidad"] = pd.to_numeric(
        base["Cantidad"], errors="coerce"
    ).fillna(0.0)

    # 🔥 eliminar basura
    base = base[base["Cantidad"] > 0]

    if base.empty:
        raise ValueError("df_resumen sin cantidades válidas")

    # =====================================================
    # NORMALIZACIÓN
    # =====================================================
    base["Materiales_norm"] = base["Materiales"].map(_norm_txt)
    base["Unidad_norm"] = base["Unidad"].map(_norm_txt)

    # =====================================================
    # MERGE (CONTROLADO)
    # =====================================================
    out = base.merge(
        df_precios,
        on=["Materiales_norm", "Unidad_norm"],
        how="left",
        validate="many_to_one",  # 🔥 evita duplicación silenciosa
    )

    # =====================================================
    # POST-PROCESO
    # =====================================================
    out["Precio Unitario"] = pd.to_numeric(
        out["Precio Unitario"], errors="coerce"
    )

    if "Moneda" not in out.columns:
        out["Moneda"] = "L"
    else:
        out["Moneda"] = out["Moneda"].fillna("L")

    # =====================================================
    # COSTO
    # =====================================================
    out["Tiene_Precio"] = (
        out["Precio Unitario"].notna()
        & (out["Precio Unitario"] > 0)
    )

    out["Costo"] = pd.NA

    mask = out["Tiene_Precio"]

    out.loc[mask, "Costo"] = (
        out.loc[mask, "Precio Unitario"]
        * out.loc[mask, "Cantidad"]
    ).round(2)

    # =====================================================
    # OUTPUT CONTRATO
    # =====================================================
    return out[
        [
            "Materiales",
            "Unidad",
            "Cantidad",
            "Precio Unitario",
            "Costo",
            "Moneda",
            "Tiene_Precio",
        ]
    ]


# =========================================================
# PRECIO DE VENTA
# =========================================================
def generar_precios_venta(
    df_costos: pd.DataFrame,
    margen: float = 0.15
) -> pd.DataFrame:

    if not isinstance(df_costos, pd.DataFrame) or df_costos.empty:
        raise ValueError("df_costos inválido")

    if "Costo" not in df_costos.columns:
        raise ValueError("df_costos no contiene 'Costo'")

    df = df_costos.copy()

    df["Precio Unitario Venta"] = pd.NA
    df["Total Venta"] = pd.NA

    mask = df["Costo"].notna()

    df.loc[mask, "Precio Unitario Venta"] = (
        df.loc[mask, "Costo"].astype(float)
        * (1 + margen)
    ).round(2)

    df.loc[mask, "Total Venta"] = (
        df.loc[mask, "Precio Unitario Venta"].astype(float)
        * df.loc[mask, "Cantidad"].astype(float)
    ).round(2)

    return df[
        [
            "Materiales",
            "Unidad",
            "Cantidad",
            "Precio Unitario Venta",
            "Total Venta",
        ]
    ]
