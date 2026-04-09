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
# ADAPTADOR PRINCIPAL (CATÁLOGO → PRECIOS)
# =========================================================
def preparar_df_precios_desde_catalogo(
    df_catalogo: pd.DataFrame,
    df_resumen: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Convierte catálogo → df_precios válido para el motor

    OUTPUT:
        df_precios
        df_faltantes
    """

    if df_catalogo is None or df_catalogo.empty:
        raise ValueError("Catálogo vacío")

    df = df_catalogo.copy()

    # =====================================================
    # NORMALIZACIÓN
    # =====================================================
    df["Materiales_norm"] = df["Materiales"].astype(str).map(_norm_txt)
    df["Unidad_norm"] = df["Unidad"].astype(str).map(_norm_txt)

    df["Precio Unitario"] = pd.to_numeric(
        df.get("Costo Unitario", df.get("Costo", 0)),
        errors="coerce"
    )

    # =====================================================
    # LIMPIEZA
    # =====================================================
    df = df[
        ["Materiales_norm", "Unidad_norm", "Precio Unitario"]
    ]

    df = df.dropna(subset=["Precio Unitario"])
    df = df[df["Precio Unitario"] > 0]

    df = df.drop_duplicates(
        subset=["Materiales_norm", "Unidad_norm"],
        keep="first"
    )

    if df.empty:
        raise ValueError("No hay precios válidos en catálogo")

    # =====================================================
    # DETECCIÓN DE FALTANTES
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
            check["Precio Unitario"].isna()
        ]

        if not faltantes.empty:
            df_faltantes = (
                faltantes[
                    ["Materiales", "Unidad", "Cantidad"]
                ]
                .drop_duplicates()
                .sort_values("Materiales")
                .reset_index(drop=True)
            )

    return df.reset_index(drop=True), df_faltantes


# =========================================================
# MOTOR DE COSTOS (CONTRATO GLOBAL DEL SISTEMA)
# =========================================================
def calcular_costos_desde_resumen(
    df_resumen: pd.DataFrame,
    df_precios: pd.DataFrame,
    df_estructuras_por_punto: pd.DataFrame,
    df_costos_estructuras: pd.DataFrame,
) -> dict:
    """
    Motor de costos alineado al sistema

    OUTPUT:
        {
            ok,
            df_costos_materiales,
            df_costos_estructuras,
            df_costos_por_punto
        }
    """

    if df_resumen is None or df_resumen.empty:
        raise ValueError("df_resumen vacío")

    if df_precios is None or df_precios.empty:
        raise ValueError("df_precios vacío")

    # =====================================================
    # 1. COSTOS DE MATERIALES
    # =====================================================
    df = df_resumen.copy()

    if "Unidad" not in df.columns:
        df["Unidad"] = ""

    df["Materiales_norm"] = df["Materiales"].astype(str).map(_norm_txt)
    df["Unidad_norm"] = df["Unidad"].astype(str).map(_norm_txt)

    df = df.merge(
        df_precios,
        on=["Materiales_norm", "Unidad_norm"],
        how="left"
    )

    if df["Precio Unitario"].isna().any():
        faltantes = df[df["Precio Unitario"].isna()]

        raise ValueError(
            "Materiales sin precio:\n" +
            faltantes[["Materiales", "Unidad"]].to_string(index=False)
        )

    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)

    df["Costo Total"] = df["Cantidad"] * df["Precio Unitario"]

    df_costos_materiales = df[
        ["Materiales", "Unidad", "Cantidad", "Precio Unitario", "Costo Total"]
    ].reset_index(drop=True)

    # =====================================================
    # 2. COSTOS DE ESTRUCTURAS
    # =====================================================
    df_costos_est = None

    if isinstance(df_costos_estructuras, pd.DataFrame) and not df_costos_estructuras.empty:
        df_costos_est = df_costos_estructuras.copy()

    # =====================================================
    # 3. COSTOS POR PUNTO (BASE SIMPLE)
    # =====================================================
    df_costos_punto = None

    if isinstance(df_estructuras_por_punto, pd.DataFrame):

        try:
            df_costos_punto = df_costos_materiales.copy()
            df_costos_punto["Punto"] = "GLOBAL"
        except Exception:
            df_costos_punto = None

    # =====================================================
    # OUTPUT FINAL
    # =====================================================
    return {
        "ok": True,
        "df_costos_materiales": df_costos_materiales,
        "df_costos_estructuras": df_costos_est,
        "df_costos_por_punto": df_costos_punto,
    }


# =========================================================
# HELPER (PREPARA ENTRADA PARA ORQUESTADOR)
# =========================================================
def construir_entrada_costos(
    data,
    df_resumen,
    df_estructuras_por_punto,
    df_costos_estructuras,
):
    """
    Construye EntradaCostos alineada al sistema
    """

    # 👇 debes tener esta función en tu infraestructura
    catalogo = obtener_catalogo_materiales(data)

    df_precios, df_faltantes = preparar_df_precios_desde_catalogo(
        catalogo,
        df_resumen
    )

    if not df_faltantes.empty:
        print("\n⚠️ MATERIALES SIN PRECIO:\n")
        print(df_faltantes.to_string(index=False))

    from costos_precios.orquestador_costos import EntradaCostos

    entrada = EntradaCostos(
        df_resumen=df_resumen,
        df_estructuras_por_punto=df_estructuras_por_punto,
        df_costos_estructuras=df_costos_estructuras,
        fuente_precios=df_precios,
    )

    return entrada
