# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import unicodedata

from entradas.base_datos import obtener_catalogo_materiales
from ayuda.debug import debug_guardar


# =========================================================
# NORMALIZACIÓN TEXTO (FIX REAL)
# =========================================================
def _norm_txt(s: object) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""

    t = str(s).upper()

    # quitar tildes
    t = "".join(
        c for c in unicodedata.normalize("NFD", t)
        if unicodedata.category(c) != "Mn"
    )

    # 🔥 limpieza fuerte para lograr match
    palabras_eliminar = [
        "DE", "DEL", "LA", "EL",
        "ANSI", "TIPO", "CLASE",
        "CARRETE", "ESPIGA", "SUSPENSION"
    ]

    for p in palabras_eliminar:
        t = t.replace(p, "")

    t = t.replace("-", " ")
    t = "".join(c if c.isalnum() else " " for c in t)
    t = " ".join(t.split())

    return t


# =========================================================
# CATÁLOGO → COSTOS UNITARIOS
# =========================================================
def preparar_df_costos_unitarios(
    df_catalogo: pd.DataFrame,
    df_resumen: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:

    if df_catalogo is None or df_catalogo.empty:
        raise ValueError("Catálogo vacío")

    df = df_catalogo.copy()

    df["Materiales_norm"] = df["Materiales"].astype(str).map(_norm_txt)
    df["Unidad_norm"] = df["Unidad"].astype(str).map(_norm_txt)

    df["Costo Unitario"] = pd.to_numeric(
        df.get("Costo Unitario", df.get("Costo", 0)),
        errors="coerce"
    )

    df = df[
        ["Materiales_norm", "Unidad_norm", "Costo Unitario"]
    ]

    df = df.dropna(subset=["Costo Unitario"])
    df = df[df["Costo Unitario"] > 0]

    df = df.drop_duplicates(
        subset=["Materiales_norm", "Unidad_norm"],
        keep="first"
    )

    if df.empty:
        raise ValueError("No hay costos válidos en catálogo")

    debug_guardar("costos_unitarios", {
        "rows": len(df),
        "cols": list(df.columns),
        "preview": df.head(5).to_dict()
    })

    # =====================================================
    # DETECCIÓN FALTANTES
    # =====================================================
    df_faltantes = pd.DataFrame()

    if df_resumen is not None and not df_resumen.empty:

        base = df_resumen.copy()

        if "Unidad" not in base.columns:
            base["Unidad"] = ""

        base["Materiales_norm"] = base["Materiales"].astype(str).map(_norm_txt)
        base["Unidad_norm"] = base["Unidad"].astype(str).map(_norm_txt)

        check = base.merge(
            df,
            on=["Materiales_norm", "Unidad_norm"],
            how="left"
        )

        faltantes = check[
            check["Costo Unitario"].isna()
        ]

        if not faltantes.empty:
            df_faltantes = (
                faltantes[
                    ["Materiales", "Unidad", "Cantidad"]
                ]
                .drop_duplicates()
                .reset_index(drop=True)
            )

            debug_guardar("costos_faltantes", {
                "faltantes": df_faltantes.to_dict()
            })

    return df.reset_index(drop=True), df_faltantes


# =========================================================
# MOTOR DE COSTOS
# =========================================================
def calcular_costos_desde_resumen(
    df_resumen: pd.DataFrame,
    df_costos: pd.DataFrame,
    df_estructuras_por_punto=None,
    df_costos_estructuras=None,
) -> pd.DataFrame:

    if df_resumen is None or df_resumen.empty:
        raise ValueError("df_resumen vacío")

    if df_costos is None or df_costos.empty:
        raise ValueError("df_costos vacío")

    df = df_resumen.copy()

    if "Unidad" not in df.columns:
        df["Unidad"] = ""

    df["Materiales_norm"] = df["Materiales"].astype(str).map(_norm_txt)
    df["Unidad_norm"] = df["Unidad"].astype(str).map(_norm_txt)

    debug_guardar("costos_input_materiales", {
        "rows": len(df),
        "preview": df.head(5).to_dict()
    })

    # MERGE
    df = df.merge(
        df_costos,
        on=["Materiales_norm", "Unidad_norm"],
        how="left"
    )

    # VALIDACIÓN
    faltantes = df[df["Costo Unitario"].isna()]
    if not faltantes.empty:
        debug_guardar("costos_error", {
            "sin_costo": faltantes[["Materiales", "Unidad"]].to_dict()
        })
        raise ValueError("Hay materiales sin costo")

    # CÁLCULO
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)
    df["Costo Total"] = df["Cantidad"] * df["Costo Unitario"]

    debug_guardar("costos_calculados", {
        "rows": len(df),
        "total": float(df["Costo Total"].sum()),
        "preview": df.head(5).to_dict()
    })

    return df[
        ["Materiales", "Unidad", "Cantidad", "Costo Unitario", "Costo Total"]
    ].reset_index(drop=True)


# =========================================================
# HELPER PRINCIPAL
# =========================================================
def construir_entrada_costos(
    data,
    df_resumen,
    df_estructuras_por_punto,
    df_materiales_por_estructura,   # 🔥 ESTE ES EL CORRECTO
):

    catalogo = obtener_catalogo_materiales(data)

    debug_guardar("costos_catalogo", {
        "rows": len(catalogo),
        "cols": list(catalogo.columns),
        "preview": catalogo.head(5).to_dict()
    })

    df_costos, df_faltantes = preparar_df_costos_unitarios(
        catalogo,
        df_resumen
    )

    debug_guardar("costos_fuente", {
        "rows": len(df_costos),
        "preview": df_costos.head(5).to_dict()
    })

    from costos_precios.orquestador_costos import EntradaCostos

    return EntradaCostos(
        df_resumen=df_resumen,
        df_estructuras_por_punto=df_estructuras_por_punto,
        df_materiales_por_estructura=df_materiales_por_estructura,  # ✅ clave
        fuente_precios=df_costos,
    )
